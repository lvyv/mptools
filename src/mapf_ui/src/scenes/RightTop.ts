import Phaser from 'phaser'
import TextureKeys from '~/consts/TextureKeys';

export default class RightTop extends Phaser.Scene {
    public static WIDTH = 418
    public static HEIGHT = 416
    constructor (handle, parent)
    {
        super(handle);

        this.parent = parent;

        this.blitter;

        this.width = 320;
        this.height = 220;
        this.depth = 1700;
        this.distance = 200;
        this.speed = 6;

        this.max = 300;
        this.xx = [];
        this.yy = [];
        this.zz = [];
    }

    create ()
    {
        this.cameras.main.setViewport(this.parent.x, this.parent.y, RightTop.WIDTH, RightTop.HEIGHT)
        // this.cameras.main.setBackgroundColor(0x0000ff)

        var bg = this.add.image(0, 0, TextureKeys.RightTopWindow).setOrigin(0).setScale(0.9)

    }

    update (time, delta)
    {

        for (var i = 0; i < this.max; i++)
        {
            var perspective = this.distance / (this.distance - this.zz[i]);

            this.zz[i] += this.speed;

            if (this.zz[i] > this.distance )
            {
                this.zz[i] -= (this.distance * 2);
            }


        }
    }

    refresh ()
    {
        this.cameras.main.setPosition(this.parent.x, this.parent.y);

        this.scene.bringToTop();
    }

}
