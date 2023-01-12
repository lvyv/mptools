export interface IFollowerConstructor {
  scene: Phaser.Scene;
  path: Phaser.Curves.Path;
  x: number;
  y: number;
  texture: string;
  frame?: string | number;
  speed?: number;
}