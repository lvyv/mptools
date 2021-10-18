{
	function MyShape()
	{
		mxCylinder.call(this);
	};

	mxUtils.extend(MyShape, mxCylinder);

	MyShape.prototype.defaultPos1 = 20;
	MyShape.prototype.defaultPos2 = 60;

	MyShape.prototype.getLabelBounds = function(rect)
	{
		 var pos1 = mxUtils.getValue(this.style, 'pos1', this.defaultPos1) * this.scale;
		 var pos2 = mxUtils.getValue(this.style, 'pos2', this.defaultPos2) * this.scale;

		 return new mxRectangle(rect.x, rect.y + pos1, rect.width, Math.min(rect.height, pos2) - Math.max(0, pos1));
	};

	MyShape.prototype.redrawPath = function(path, x, y, w, h, isForeground)
	{
		 var pos1 = mxUtils.getValue(this.style, 'pos1', this.defaultPos1);
		 var pos2 = mxUtils.getValue(this.style, 'pos2', this.defaultPos2);
		 var polycords = JSON.parse(mxUtils.getValue(this.style, 'polyCoords'));

		if (isForeground)
		{

			path.moveTo(polycords[0][0], polycords[0][1]);
			path.lineTo(polycords[1][0], polycords[1][1])

			path.moveTo(polycords[1][0], polycords[1][1]);
			path.lineTo(polycords[2][0], polycords[2][1])

			path.moveTo(polycords[2][0], polycords[2][1]);
			path.lineTo(polycords[3][0], polycords[3][1])

			path.moveTo(polycords[3][0], polycords[3][1]);
			path.lineTo(polycords[0][0], polycords[0][1])

		}
		else
		{
			path.rect(0, 0, w, h);
		}
	};

	mxCellRenderer.registerShape('casicloud.polygon', MyShape);

	mxVertexHandler.prototype.createCustomHandles = function()
	{
		if (this.state.style['shape'] == 'casicloud.polygon')
		{
			// Implements the handle for the hndr
			var hndr1 = new mxHandle(this.state);
			var coords = JSON.parse(mxUtils.getValue(this.state.style, 'polyCoords'));
			hndr1.getPosition = function(bounds)
			{
				// var pos1 = Math.max(0, Math.min(bounds.height, parseFloat(mxUtils.getValue(this.state.style, 'pos1', MyShape.prototype.defaultPos1))));
				// var pos2 = Math.max(pos1, Math.min(bounds.height, parseFloat(mxUtils.getValue(this.state.style, 'pos2', MyShape.prototype.defaultPos2))));

				return new mxPoint(bounds.x + coords[0][0], bounds.y + coords[0][1]);
			};
			hndr1.setPosition = function(bounds, pt)
			{
				coords[0][0] = pt.x - bounds.x;
				coords[0][1] = pt.y - bounds.y;
				this.state.style['polyCoords'] = JSON.stringify(coords);
			};
			hndr1.execute = function()
			{
				this.copyStyle('polyCoords');
			}
			hndr1.ignoreGrid = true;

			var hndr2 = new mxHandle(this.state);
			var coords = JSON.parse(mxUtils.getValue(this.state.style, 'polyCoords'));
			hndr2.getPosition = function(bounds)
			{
				return new mxPoint(bounds.x + coords[1][0], bounds.y + coords[1][1]);
			};
			hndr2.setPosition = function(bounds, pt)
			{
				coords[1][0] = pt.x - bounds.x;
				coords[1][1] = pt.y - bounds.y;
				this.state.style['polyCoords'] = JSON.stringify(coords);
			};
			hndr2.execute = function()
			{
				this.copyStyle('polyCoords');
			}
			hndr2.ignoreGrid = true;

			var hndr3 = new mxHandle(this.state);
			var coords = JSON.parse(mxUtils.getValue(this.state.style, 'polyCoords'));
			hndr3.getPosition = function(bounds)
			{
				return new mxPoint(bounds.x + coords[2][0], bounds.y + coords[2][1]);
			};
			hndr3.setPosition = function(bounds, pt)
			{
				coords[2][0] = pt.x - bounds.x;
				coords[2][1] = pt.y - bounds.y;
				this.state.style['polyCoords'] = JSON.stringify(coords);
			};
			hndr3.execute = function()
			{
				this.copyStyle('polyCoords');
			}
			hndr3.ignoreGrid = true;

			var hndr4 = new mxHandle(this.state);
			var coords = JSON.parse(mxUtils.getValue(this.state.style, 'polyCoords'));
			hndr4.getPosition = function(bounds)
			{
				return new mxPoint(bounds.x + coords[3][0], bounds.y + coords[3][1]);
			};
			hndr4.setPosition = function(bounds, pt)
			{
				coords[3][0] = pt.x - bounds.x;
				coords[3][1] = pt.y - bounds.y;
				this.state.style['polyCoords'] = JSON.stringify(coords);
			};
			hndr4.execute = function()
			{
				this.copyStyle('polyCoords');
			}
			hndr4.ignoreGrid = true;

			return [hndr1, hndr2, hndr3, hndr4];
		}

		return null;
	};

	mxVertexHandler.prototype.livePreview = true;
}