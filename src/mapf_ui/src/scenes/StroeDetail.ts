import Phaser from 'phaser'
import TextureKeys from '~/consts/TextureKeys';

export default class StoreDetail extends Phaser.Scene {
    public static WIDTH = 402
    public static HEIGHT = 418
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
        this.cameras.main.setViewport(this.parent.x, this.parent.y, StoreDetail.WIDTH, StoreDetail.HEIGHT)
        // this.cameras.main.setBackgroundColor(0x0000ff)

        this.blitter = this.add.blitter(0, 0, TextureKeys.Star)

        for (var i = 0; i < this.max; i++)
        {
            this.xx[i] = Math.floor(Math.random() * this.width ) - (this.width / 2)
            this.yy[i] = Math.floor(Math.random() * this.height ) - (this.height / 2)
            this.zz[i] = Math.floor(Math.random() * this.depth) - 100

            var perspective = this.distance / (this.distance - this.zz[i])
            var x = (this.width / 2) + this.xx[i] * perspective
            var y = (this.height / 2) + this.yy[i] * perspective
            // var a = (x < 0 || x > 320 || y < 20 || y > 260) ? 0 : 1;
            this.blitter.create(x, y)
        }
        // this.add.image(0,0, TextureKeys.GreenPanel).setAlpha(0.5)
        var bg = this.add.image(0, 0, TextureKeys.StoreDetailWindow).setOrigin(0).setScale(0.94)

    }

    update (time, delta)
    {
        var list = this.blitter.children.list;

        for (var i = 0; i < this.max; i++)
        {
            var perspective = this.distance / (this.distance - this.zz[i]);

            var x = (this.width / 2) + this.xx[i] * perspective;
            var y = (this.height / 2) + this.yy[i] * perspective;

            this.zz[i] += this.speed;

            if (this.zz[i] > this.distance )
            {
                this.zz[i] -= (this.distance * 2);
            }

            list[i].x = x;
            list[i].y = y;
            list[i].a = (x < 0 || x > 320 || y < 20 || y > 260) ? 0 : 1;
        }
    }

    refresh ()
    {
        this.cameras.main.setPosition(this.parent.x, this.parent.y);

        this.scene.bringToTop();
    }

}
