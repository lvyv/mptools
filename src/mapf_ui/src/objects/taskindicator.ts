export class TaskIndicator extends Phaser.GameObjects.Container {
  private start: Phaser.GameObjects.Image;
  private end: Phaser.GameObjects.Image;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    let start = scene.add.image(0, 0, 'tankRed');
    let end = scene.add.image(0, 0, 'end');
    super(scene, x, y, [start, end]);

    this.setSize(start.width, start.height);
    this.setInteractive();
    scene.input.setDraggable(this);

    this.on('pointerover', function () {
      start.setTint(0x44ff44);
      end.setTint(0x44ff44);
    });
    this.on('pointerout', function () {
      start.clearTint();
      end.clearTint();
    });

    scene.input.on('drag', function (pointer: Phaser.Input.Pointer, gameObject: Phaser.GameObjects.Image, dragX: number, dragY: number) {
      gameObject.x = dragX;
      gameObject.y = dragY;
    });

    this.start = start;
    this.end = end;
  }

  update(): void {
  }
}
