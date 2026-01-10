import gi
import math
import cairo
from typing import Iterable, Literal, Tuple
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.utils.helpers import clamp

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, GObject


class CircularScale(CircularProgressBar):
    def __init__(
        self,
        cap_delta: float = 0.01,
        value: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 1.0,
        start_angle: float | None = None,
        end_angle: float | None = None,
        line_width: int = 4,
        line_style: (
            Literal["none", "butt", "round", "square"] | cairo.LineCap
        ) = cairo.LineCap.ROUND,
        pie: bool = False,
        invert: bool = False,
        child: Gtk.Widget | None = None,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: (
            Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None
        ) = None,
        v_align: (
            Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None
        ) = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        self.cap_delta = cap_delta
        super().__init__(
            value=value,
            min_value=min_value,
            max_value=max_value,
            start_angle=start_angle,
            end_angle=end_angle,
            line_width=line_width,
            line_style=line_style,
            pie=pie,
            invert=invert,
            child=child,
            name=name,
            visible=visible,
            all_visible=all_visible,
            style=style,
            style_classes=style_classes,
            tooltip_text=tooltip_text,
            tooltip_markup=tooltip_markup,
            h_align=h_align,
            v_align=v_align,
            h_expand=h_expand,
            v_expand=v_expand,
            size=size,
            **kwargs,
        )
        # gadgets
        self._trough_ctx = self.do_create_gadget_context("trough")
        self._slider_ctx = self.do_create_gadget_context("slider")
        self._highlight_ctx = self.do_create_gadget_context("highlight")

    def do_get_border_width(
        self, context: Gtk.StyleContext, state: Gtk.StateFlags
    ) -> float:
        border = context.get_border(state)  # type: ignore
        return max(
            self._line_width,
            border.top,  # type: ignore
            border.bottom,  # type: ignore
            border.left,  # type: ignore
            border.right,  # type: ignore
            context.get_property("min-width", state),  # type: ignore
            context.get_property("min-height", state),  # type: ignore
        )

    def do_calculate_safe_radius(
        self,
        radius: float,
        slider_height: float,
        progress_thickness: float,
        trough_thickness: float,
    ) -> float:
        return max(
            radius - max(slider_height, progress_thickness, trough_thickness) / 2, 0
        )

    def do_normalize_value(self) -> float:
        value_range = self._max_value - self._min_value
        if value_range == 0:
            return 0.0
        return clamp((self._value - self._min_value) / value_range, 0.0, 1.0)

    def do_get_arc_delta(self) -> float:
        # add a tiny delta to force the rendering of line caps. (square and butt)
        return self.cap_delta if self.line_style != cairo.LineCap.ROUND else 0.0

    def do_draw_progress_arc(
        self,
        cr: cairo.Context,
        center_x: float,
        center_y: float,
        radius: float,
        start_angle: float,
        progress_thickness: float,
        progress_angle: float,
        progress_color: Gdk.RGBA,
        slider_thickness_angle: float,
        left_gap_angle: float,
    ) -> None:
        cr.set_line_width(progress_thickness)
        Gdk.cairo_set_source_rgba(cr, progress_color)

        progress_line_width_angle = progress_thickness / radius

        if progress_angle - progress_line_width_angle - left_gap_angle > start_angle:
            # draw normal arc
            arc_start = (
                start_angle + (progress_line_width_angle - slider_thickness_angle) / 2
            )
            arc_end = (
                progress_angle
                - (progress_line_width_angle / 2 + slider_thickness_angle / 2)
                - left_gap_angle
            )
            cr.arc(center_x, center_y, radius, arc_start, arc_end)
            cr.stroke()
            return

        # draw shrinking dot when available space is minimal
        ratio = progress_line_width_angle / (progress_line_width_angle + left_gap_angle)
        dot_arc = -(start_angle - progress_angle) / 2 * ratio
        dot_radius = 2 * radius * math.sin(dot_arc)

        cr.set_line_width(dot_radius)
        true_start = start_angle - slider_thickness_angle / 2 + dot_arc
        delta = self.do_get_arc_delta()
        cr.arc(center_x, center_y, radius, true_start, true_start + delta)
        cr.stroke()
        cr.set_line_width(radius * progress_line_width_angle)

    def do_draw_slider(
        self,
        cr: cairo.Context,
        center_x: float,
        center_y: float,
        radius: float,
        progress_angle: float,
        slider_color: Gdk.RGBA,
        slider_thickness_angle: float,
        slider_height: float,
        corner_radius: float | Tuple[float, float, float, float],
    ) -> None:
        angle_rad = progress_angle
        sx = center_x + math.cos(angle_rad) * radius
        sy = center_y + math.sin(angle_rad) * radius

        cr.save()
        cr.translate(sx, sy)
        cr.rotate(angle_rad + math.pi / 2)

        Gdk.cairo_set_source_rgba(cr, slider_color)

        self.do_draw_rounded_rect(
            cr,
            -(slider_thickness_angle * radius) / 2,
            -slider_height / 2,
            slider_thickness_angle * radius,
            slider_height,
            corner_radius,
        )
        cr.fill()
        cr.restore()

    def do_draw_trough_arc(
        self,
        cr: cairo.Context,
        center_x: float,
        center_y: float,
        radius: float,
        progress_angle: float,
        real_end_angle: float,
        trough_color: Gdk.RGBA,
        trough_thickness: float,
        slider_thickness_angle: float,
        right_gap_angle: float,
    ) -> None:
        cr.set_line_width(trough_thickness)
        Gdk.cairo_set_source_rgba(cr, trough_color)

        trough_line_width_angle = trough_thickness / radius

        remaining_start = (
            progress_angle + trough_line_width_angle / 2 + slider_thickness_angle / 2
        )
        remaining_end = (
            real_end_angle - slider_thickness_angle / 2 - trough_line_width_angle / 2
        )

        if remaining_start < remaining_end - right_gap_angle:
            # draw arc
            cr.arc(
                center_x,
                center_y,
                radius,
                remaining_start + right_gap_angle,
                remaining_end,
            )
            cr.stroke()
            return

        # draw shrinking dot when remaining space is minimal
        ratio = trough_line_width_angle / (trough_line_width_angle + right_gap_angle)
        remaining_angle = real_end_angle - (slider_thickness_angle + progress_angle)
        remaining_usable_angle = max(remaining_angle, 0.0) * ratio

        chord_length = 2 * radius * math.sin(remaining_usable_angle / 2)
        cr.set_line_width(chord_length)

        mid_angle = (
            progress_angle
            + slider_thickness_angle / 2
            + remaining_angle * (1 - ratio)
            + remaining_usable_angle / 2
        )
        delta = self.do_get_arc_delta()
        cr.arc(center_x, center_y, radius, mid_angle, mid_angle + delta)
        cr.stroke()

    def do_create_gadget_context(self, node_name: str) -> Gtk.StyleContext:
        ctx = Gtk.StyleContext()
        ctx.set_parent(self.get_style_context())  # type: ignore

        path = self.get_style_context().get_path().copy()  # type: ignore
        path.append_type(GObject.TYPE_NONE)
        path.iter_set_object_name(-1, node_name)

        ctx.connect("changed", lambda _: self.queue_draw())
        ctx.set_path(path)  # type: ignore
        return ctx

    def do_draw_rounded_rect(
        self,
        cr: cairo.Context,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float | Tuple[float, float, float, float],
    ) -> None:
        if isinstance(radius, (int, float)):
            rtl = rtr = rbr = rbl = float(radius)
        else:
            rtl, rtr, rbr, rbl = map(float, radius)

        rtl, rtr, rbr, rbl = (max(0.0, v) for v in (rtl, rtr, rbr, rbl))

        # for scaling down overflowing corner radius
        factor = min(
            1.0,
            width / (rtl + rtr) if (rtl + rtr) > width else 1.0,  # top edge
            width / (rbl + rbr) if (rbl + rbr) > width else 1.0,  # bottom edge
            height / (rtl + rbl) if (rtl + rbl) > height else 1.0,  # left edge
            height / (rtr + rbr) if (rtr + rbr) > height else 1.0,  # right edge
        )

        rtl, rtr, rbr, rbl = (r * factor for r in (rtl, rtr, rbr, rbl))

        cr.new_sub_path()

        if rtl == rtr == rbr == rbl == 0:
            cr.rectangle(x, y, width, height)
            return

        # top-left (after the corner curve)
        cr.move_to(x + rtl, y)

        # top edge & top-right corner
        cr.line_to(x + width - rtr, y)
        if rtr > 0:
            cr.arc(x + width - rtr, y + rtr, rtr, -math.pi / 2, 0)

        # right edge & bottom-right corner
        cr.line_to(x + width, y + height - rbr)
        if rbr > 0:
            cr.arc(x + width - rbr, y + height - rbr, rbr, 0, math.pi / 2)

        # bottom edge & bottom-left corner
        cr.line_to(x + rbl, y + height)
        if rbl > 0:
            cr.arc(x + rbl, y + height - rbl, rbl, math.pi / 2, math.pi)

        # left edge & top-left corner
        cr.line_to(x, y + rtl)
        if rtl > 0:
            cr.arc(x + rtl, y + rtl, rtl, math.pi, 3 * math.pi / 2)

        cr.close_path()

    def do_draw(self, cr: cairo.Context) -> None:
        state = self.get_state_flags()
        style_context = self.get_style_context()

        background_color = style_context.get_background_color(state)  # type: ignore

        width = self.get_allocated_width()
        height = self.get_allocated_height()
        center_x = width / 2
        center_y = height / 2

        # slider properties
        slider_color = self._slider_ctx.get_background_color(state)  # type: ignore
        slider_height = self._slider_ctx.get_property("min-height", state)  # type: ignore
        slider_thickness = self._slider_ctx.get_property("min-width", state)  # type: ignore
        left_gap = self._slider_ctx.get_property("margin-left", state)  # type: ignore
        right_gap = self._slider_ctx.get_property("margin-right", state)  # type: ignore
        corner_radius = self._slider_ctx.get_property("border-radius", state)  # type: ignore

        # progress (highlight) properties
        progress_color = self._highlight_ctx.get_background_color(state)  # type: ignore
        progress_thickness = self.do_get_border_width(self._highlight_ctx, state)

        # trough properties
        trough_color = self._trough_ctx.get_background_color(state)  # type: ignore
        trough_thickness = self.do_get_border_width(self._trough_ctx, state)

        # calculate radius
        radius = self.do_calculate_radius()
        safe_radius = self.do_calculate_safe_radius(
            radius, slider_height, progress_thickness, trough_thickness
        )
        if safe_radius == 0:
            if child := self.get_child():
                self.propagate_draw(child, cr)
            return

        cr.save()
        cr.set_line_cap(self._line_style)

        # background fill
        cr.set_line_width(0)
        Gdk.cairo_set_source_rgba(cr, background_color)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

        # angles (S = r*theta)
        left_gap_angle = left_gap / safe_radius
        right_gap_angle = right_gap / safe_radius
        slider_thickness_angle = slider_thickness / safe_radius

        start_angle = math.radians(self._start_angle)
        end_angle = (
            math.radians(self._end_angle) - slider_thickness_angle - right_gap_angle
        )
        real_end_angle = math.radians(self._end_angle) - right_gap_angle

        normalized_value = self.do_normalize_value()
        progress_angle = start_angle + normalized_value * (end_angle - start_angle)

        # exposed for override
        self.do_draw_progress_arc(
            cr=cr,
            center_x=center_x,
            center_y=center_y,
            radius=safe_radius,
            start_angle=start_angle,
            progress_angle=progress_angle,
            progress_color=progress_color,
            progress_thickness=progress_thickness,
            slider_thickness_angle=slider_thickness_angle,
            left_gap_angle=left_gap_angle,
        )

        self.do_draw_slider(
            cr=cr,
            center_x=center_x,
            center_y=center_y,
            radius=safe_radius,
            progress_angle=progress_angle,
            slider_color=slider_color,
            slider_thickness_angle=slider_thickness_angle,
            slider_height=slider_height,
            corner_radius=corner_radius,
        )

        self.do_draw_trough_arc(
            cr=cr,
            center_x=center_x,
            center_y=center_y,
            radius=safe_radius,
            progress_angle=progress_angle,
            real_end_angle=real_end_angle,
            trough_color=trough_color,
            trough_thickness=trough_thickness,
            slider_thickness_angle=slider_thickness_angle,
            right_gap_angle=right_gap_angle,
        )

        # draw child (if any)
        if child := self.get_child():
            self.propagate_draw(child, cr)

        cr.restore()
        return
