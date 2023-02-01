import Phaser from 'phaser'
import TextureKeys from '~/consts/TextureKeys';

export default class RightTop extends Phaser.Scene {
    public static WIDTH = 418
    public static HEIGHT = 416
    constructor (handle, parent)
    {
        super(handle);
        this.parent = parent;
    }

    create ()
    {
        this.cameras.main.setViewport(this.parent.x, this.parent.y, RightTop.WIDTH, RightTop.HEIGHT)
        this.add.image(0, 0, TextureKeys.RightTopWindow).setOrigin(0).setScale(0.9)
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
