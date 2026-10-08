#!/usr/bin/env python3
"""M4b 验证：AGS 沙盒 → 自建 VPS PostgreSQL（公网直连）

验证内容：
  1. 平台侧（本机）在 VPS PG 上「建库 + 建角色 + 授权」；
  2. AGS 沙盒内 TCP 可达 VPS PG 的公网端口；
  3. 沙盒内用「每游戏 role」实际连接并读写（sslmode=disable / require 分别测）。

用法：
  cd test/infra/sandbox
  set -a; source .env; set +a
  VPS_PG_PASSWORD=xxx uv run --with e2b --with "psycopg[binary]" python m4b_vps_pg_verify.py
"""

import os
import secrets
import time

import psycopg
from e2b import Sandbox

HOST = os.environ.get("VPS_PG_HOST", "152.32.215.89")
PORT = int(os.environ.get("VPS_PG_PORT", "10050"))
ADMIN_USER = os.environ.get("VPS_PG_USER", "root")
ADMIN_PWD = os.environ["VPS_PG_PASSWORD"]

GAME_ID = "game_m4b_probe"
ROLE = f"{GAME_ID}_rw"
PWD = secrets.token_urlsafe(16)

PIP_MIRROR = "https://mirrors.cloud.tencent.com/pypi/simple"

PROBE = f"""\
import psycopg2

for sslmode in ("disable", "require"):
    try:
        conn = psycopg2.connect(
            host="{HOST}", port={PORT}, dbname="{GAME_ID}",
            user="{ROLE}", password="{PWD}", connect_timeout=10, sslmode=sslmode,
        )
        cur = conn.cursor()
        cur.execute("select current_user, current_database(), inet_server_addr()::text")
        print("RESULT", sslmode, "OK", cur.fetchone())
        cur.execute("create table if not exists t(id serial primary key, v text)")
        cur.execute("insert into t(v) values ('from-sandbox')")
        conn.commit()
        cur.execute("select count(*) from t")
        print("RESULT", sslmode, "WRITE rows =", cur.fetchone()[0])
        conn.close()
    except Exception as e:
        print("RESULT", sslmode, "FAIL", repr(e)[:220])
"""


def admin(sql, db="postgres"):
    dsn = f"host={HOST} port={PORT} dbname={db} user={ADMIN_USER} password={ADMIN_PWD} connect_timeout=10"
    with psycopg.connect(dsn, autocommit=True) as c:
        cur = c.execute(sql)
        return cur.fetchall() if cur.description else None


def provision():
    admin(f'DROP DATABASE IF EXISTS "{GAME_ID}"')
    admin(f'DROP ROLE IF EXISTS "{ROLE}"')
    admin(f'CREATE DATABASE "{GAME_ID}"')
    admin(f"CREATE ROLE \"{ROLE}\" LOGIN PASSWORD '{PWD}'")
    admin(f'GRANT CONNECT ON DATABASE "{GAME_ID}" TO "{ROLE}"')
    admin('GRANT ALL ON SCHEMA public TO "%s"' % ROLE, db=GAME_ID)
    print(f"[provision] db={GAME_ID} role={ROLE}")


def cleanup():
    try:
        admin(f"select pg_terminate_backend(pid) from pg_stat_activity where datname='{GAME_ID}'")
        admin(f'DROP DATABASE IF EXISTS "{GAME_ID}"')
        admin(f'DROP ROLE IF EXISTS "{ROLE}"')
        print("[cleanup] done")
    except Exception as e:
        print("[cleanup] error:", repr(e)[:200])


def pick_python(sbx):
    """找出一个已装 psycopg2 的 python，否则返回首选解释器。"""
    r = sbx.commands.run(
        "which -a python3 2>/dev/null; which python 2>/dev/null", user="root"
    )
    pythons = list(dict.fromkeys(l.strip() for l in r.stdout.splitlines() if l.strip()))
    for py in pythons:
        out = sbx.commands.run(f"{py} -c 'import psycopg2' >/dev/null 2>&1 && echo YES || echo NO", user="root")
        if out.stdout.strip() == "YES":
            return py, True
    return (pythons[0] if pythons else "python3"), False


def main():
    provision()
    sbx = None
    try:
        sbx = Sandbox.create(
            template=os.environ.get("AGS_TEMPLATE", "ai-game-platform-test-aio"),
            timeout=1200,
        )
        print(f"[sandbox] {sbx.sandbox_id}")

        py, has_driver = pick_python(sbx)
        print(f"[python] {py}  psycopg2={'已装' if has_driver else '缺失'}")

        if not has_driver:
            sbx.commands.run(
                f"{py} -m pip install --user -i {PIP_MIRROR} psycopg2-binary"
                " > /tmp/pip.log 2>&1; echo $? > /tmp/pip.rc",
                user="root",
                background=True,
            )
            print(f"[pip] 后台安装（腾讯云镜像 {PIP_MIRROR}）")

        r = sbx.commands.run(
            f"timeout 8 bash -c 'cat < /dev/null > /dev/tcp/{HOST}/{PORT}' && echo OPEN || echo UNREACHABLE",
            user="root",
        )
        print(f"[tcp {HOST}:{PORT}] {r.stdout.strip()}")

        if not has_driver:
            rc = None
            for _ in range(150):  # 最多 300s
                out = sbx.commands.run("cat /tmp/pip.rc 2>/dev/null || echo RUNNING", user="root").stdout.strip()
                if out and out != "RUNNING":
                    rc = out
                    break
                time.sleep(2)
            print(f"[pip] rc={rc}")
            if rc != "0":
                print(sbx.commands.run("tail -c 400 /tmp/pip.log", user="root").stdout)
                return

        sbx.files.write("/tmp/m4b_probe.py", PROBE)
        t0 = time.time()
        r = sbx.commands.run(f"{py} /tmp/m4b_probe.py", user="root", timeout=180)
        print(f"[probe] {time.time() - t0:.1f}s")
        print(r.stdout.strip())
        if r.stderr.strip():
            print("[stderr]", r.stderr.strip()[-300:])
    finally:
        if sbx:
            sbx.kill()
            print("[sandbox] killed")
        cleanup()


if __name__ == "__main__":
    main()
