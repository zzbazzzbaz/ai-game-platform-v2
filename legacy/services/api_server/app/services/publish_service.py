from html.parser import HTMLParser

from sqlalchemy.orm import Session

from app.core.constants import (
    FILENAME_PATTERN,
    INLINE_REF_PREFIXES,
    INLINE_RESOURCE_ATTRS,
    INPUT_EXTENSIONS,
    MAX_HTML_BYTES,
    MAX_INPUT_BYTES,
    MAX_SCRIPT_BYTES,
)
from app.core.exceptions import ValidationError
from app.gateways.minio import MinioGateway, input_key
from app.services.session_service import check_owner, check_thread_id


class _RefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_html = False
        self.has_script = False
        self.in_inline_script = False
        self.scripts: list[str] = []
        self.bad_refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name == "html":
            self.has_html = True
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if name == "script":
            self.has_script = True
            src = attr_map.get("src", "")
            if src:
                if not _is_inlineable_ref(src):
                    self.bad_refs.append(f"script src={src}")
            else:
                self.in_inline_script = True
                self.scripts.append("")
        for attr in INLINE_RESOURCE_ATTRS.get(name, ()):
            if name == "script" and attr == "src":
                continue
            ref = attr_map.get(attr, "")
            if ref and not _is_inlineable_ref(ref):
                self.bad_refs.append(f"{name} {attr}={ref}")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self.in_inline_script = False

    def handle_data(self, data: str) -> None:
        if self.in_inline_script and self.scripts:
            self.scripts[-1] += data


def _is_inlineable_ref(ref: str) -> bool:
    return ref.strip().lower().startswith(INLINE_REF_PREFIXES)


def validate_index_html(html: bytes) -> list[str]:
    """校验单文件游戏产物：体积/编码/结构/无外链/含内联脚本。"""
    if not html:
        raise ValidationError("index.html 为空，无法发布")
    if len(html) > MAX_HTML_BYTES:
        raise ValidationError(f"index.html 超过 {MAX_HTML_BYTES // (1024 * 1024)}MB，无法发布")
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError("index.html 不是合法 UTF-8 编码") from None
    lowered = text.lower()
    if "<html" not in lowered or "</html>" not in lowered:
        raise ValidationError("index.html 缺少 <html> 结构")
    collector = _RefCollector()
    try:
        collector.feed(text)
    except Exception as e:
        raise ValidationError(f"index.html 解析失败：{e}") from e
    if not collector.has_html:
        raise ValidationError("index.html 缺少 <html> 结构")
    if collector.bad_refs:
        raise ValidationError(
            "index.html 引用了外部文件，单文件发布不允许：" + "；".join(collector.bad_refs[:5])
        )
    if not collector.has_script:
        raise ValidationError("index.html 缺少 <script>，不是可玩游戏")
    scripts = [s for s in (b.strip() for b in collector.scripts) if s]
    if not scripts:
        raise ValidationError("index.html 没有内联游戏代码")
    if sum(len(s) for s in scripts) > MAX_SCRIPT_BYTES:
        raise ValidationError(f"内联脚本超过 {MAX_SCRIPT_BYTES // (1024 * 1024)}MB，无法发布")
    return scripts


def check_input_file(filename: str, size: int) -> None:
    if not FILENAME_PATTERN.match(filename):
        raise ValidationError("文件名非法：只允许字母数字及 _.-，且不能以点开头")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in INPUT_EXTENSIONS:
        raise ValidationError("素材只支持图片与文本：png/jpg/gif/webp/svg/txt/md/json/csv")
    if size > MAX_INPUT_BYTES:
        raise ValidationError("素材超过 5MB")


def store_input(
    *,
    thread_id: str,
    user_id: str,
    filename: str,
    data: bytes,
    content_type: str,
    session: Session,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    check_owner(session, thread_id, user_id, must_exist=True)
    check_input_file(filename, len(data))
    minio.put_bytes(input_key(thread_id, filename), data, content_type)
    return {"filename": filename, "size": len(data)}
