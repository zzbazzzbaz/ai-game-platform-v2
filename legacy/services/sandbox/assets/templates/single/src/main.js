import Phaser from 'phaser';
import { clamp } from './logic.js';

// 【模板】Phaser 配置 + 场景注册。生成区只写 src/scenes/**、src/logic.js、src/textures.js 等。
class MainScene extends Phaser.Scene {
  constructor() {
    super('Main');
  }

  create() {
    const { width, height } = this.scale;
    this.add
      .text(width / 2, height / 2, '游戏模板', {
        fontFamily: 'sans-serif',
        fontSize: `${clamp(Math.round(width / 18), 20, 48)}px`,
        color: '#ffffff',
      })
      .setOrigin(0.5);
  }
}

export const gameConfig = {
  type: Phaser.AUTO,
  parent: 'game',
  width: 960,
  height: 540,
  backgroundColor: '#10131a',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [MainScene],
};

export function startGame() {
  return new Phaser.Game(gameConfig);
}

if (typeof window !== 'undefined') {
  window.__GAME__ = startGame();
}
