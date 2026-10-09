// 【模板】esbuild 打包：把 src/main.js 及其依赖（含 Phaser）打成单文件 dist/index.html。
// 资源（图片/音频）走 data URI 内联，保证产物零外部依赖。
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { build } from 'esbuild';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const INLINE_LOADERS = {
  '.png': 'dataurl',
  '.jpg': 'dataurl',
  '.jpeg': 'dataurl',
  '.gif': 'dataurl',
  '.webp': 'dataurl',
  '.svg': 'dataurl',
  '.mp3': 'dataurl',
  '.wav': 'dataurl',
  '.ogg': 'dataurl',
};

const ENTRY_TAG = /<script\b[^>]*\bsrc=["']\.\/src\/main\.js["'][^>]*><\/script>/i;

async function main() {
  const result = await build({
    absWorkingDir: root,
    entryPoints: [join(root, 'src/main.js')],
    bundle: true,
    format: 'iife',
    target: 'es2020',
    minify: true,
    write: false,
    legalComments: 'none',
    loader: INLINE_LOADERS,
  });

  const js = result.outputFiles[0].text;
  const shell = await readFile(join(root, 'index.html'), 'utf8');
  if (!ENTRY_TAG.test(shell)) {
    throw new Error('index.html 缺少 <script src="./src/main.js"> 入口标签');
  }
  // 转义 </script，避免包内字符串提前闭合内联脚本
  const safeJs = js.replace(/<\/script/gi, '<\\/script');
  // 用函数替换器：替换串中的 $& / $` 等不会被当成特殊模式
  const html = shell.replace(ENTRY_TAG, () => `<script>${safeJs}</script>`);

  await mkdir(join(root, 'dist'), { recursive: true });
  await writeFile(join(root, 'dist/index.html'), html);
  console.log(`构建完成：dist/index.html（${Buffer.byteLength(html)} 字节）`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
