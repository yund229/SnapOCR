"""标注编辑器纯逻辑测试:马赛克生成与操作渲染(不依赖 GUI)。"""

from PIL import Image

from snapocr.editor import make_mosaic, render_ops


def _white_image(size=(100, 80)):
    return Image.new("RGB", size, "white")


class TestMakeMosaic:
    def test_same_size(self):
        img = _white_image()
        assert make_mosaic(img).size == img.size

    def test_pixelates_uniform_patch(self):
        # 左半红右半白,马赛克后各块颜色应块内平均,不再出现跨块渐变细节
        img = Image.new("RGB", (100, 100), "white")
        for x in range(50):
            for y in range(100):
                img.putpixel((x, y), (255, 0, 0))
        mosaic = make_mosaic(img, block=10)
        # (55,5) 位于 x=50 起的整块白块内,不应残留红色
        assert mosaic.getpixel((55, 5)) != (255, 0, 0)
        # 整块全红的 (5,5) 保持红色
        assert mosaic.getpixel((5, 5)) == (255, 0, 0)

    def test_original_untouched(self):
        img = _white_image()
        make_mosaic(img)
        assert img.getpixel((0, 0)) == (255, 255, 255)


class TestRenderOps:
    def test_empty_ops_returns_copy(self):
        img = _white_image()
        out = render_ops(img, [])
        assert out.size == img.size
        assert out.getpixel((0, 0)) == (255, 255, 255)

    def test_rect_draws_outline(self):
        img = _white_image((100, 100))
        ops = [{"type": "rect", "box": (10, 10, 90, 90), "color": "#ff0000", "width": 3}]
        out = render_ops(img, ops)
        assert out.getpixel((10, 50)) == (255, 0, 0)   # 左边框
        assert out.getpixel((50, 10)) == (255, 0, 0)   # 上边框
        assert out.getpixel((50, 50)) == (255, 255, 255)  # 内部仍为白

    def test_pen_single_point_draws_dot(self):
        img = _white_image((50, 50))
        ops = [{"type": "pen", "points": [(25, 25)], "color": "#0000ff", "width": 6}]
        out = render_ops(img, ops)
        assert out.getpixel((25, 25)) == (0, 0, 255)

    def test_pen_line_covers_points(self):
        img = _white_image((100, 20))
        ops = [{"type": "pen", "points": [(5, 10), (50, 10), (95, 10)],
                "color": "#000000", "width": 5}]
        out = render_ops(img, ops)
        assert out.getpixel((50, 10)) == (0, 0, 0)

    def test_mosaic_changes_region(self):
        img = _white_image((100, 100))
        ops = [{"type": "mosaic", "points": [(50, 50)], "width": 6}]
        out = render_ops(img, ops)
        # 白底图上马赛克视觉上仍是白,验证渲染不崩溃且尺寸不变
        assert out.size == img.size

    def test_mosaic_visible_on_colored_image(self):
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        for x in range(50):
            for y in range(100):
                img.putpixel((x, y), (255, 0, 0))
        for x in range(50, 100):
            for y in range(100):
                img.putpixel((x, y), (0, 0, 255))
        ops = [{"type": "mosaic", "points": [(50, 50)], "width": 6}]
        out = render_ops(img, ops)
        # 边界块被平均化,不再纯红
        assert out.getpixel((50, 50)) != (255, 0, 0)

    def test_does_not_modify_base(self):
        img = _white_image((60, 60))
        ops = [{"type": "rect", "box": (5, 5, 55, 55), "color": "#00ff00", "width": 2}]
        render_ops(img, ops)
        assert img.getpixel((5, 30)) == (255, 255, 255)
