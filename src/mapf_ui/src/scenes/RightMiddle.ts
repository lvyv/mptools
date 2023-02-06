import Phaser from 'phaser'
import TextureKeys from '~/consts/TextureKeys';

export default class RightMiddle extends Phaser.Scene {
    public static WIDTH = 419
    public static HEIGHT = 197
    constructor (handle, parent)
    {
        super(handle);
        this.parent = parent;
    }

    create ()
    {
        this.cameras.main.setViewport(this.parent.x, this.parent.y, RightMiddle.WIDTH, RightMiddle.HEIGHT)

        this.add.image(0, 0, TextureKeys.RightMiddleWindow).setOrigin(0).setScale(0.9)

    }

    update (time, delta)
    {

    }

    refresh ()
    {
        this.cameras.main.setPosition(this.parent.x, this.parent.y);
        this.scene.bringToTop();
    }

}
