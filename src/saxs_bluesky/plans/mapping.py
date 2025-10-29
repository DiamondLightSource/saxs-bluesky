# BL = get_saxs_beamline()
# CONFIG = load_beamline_config()
# DEFAULT_PANDA = CONFIG.DEFAULT_PANDA
# FAST_DETECTORS = CONFIG.FAST_DETECTORS
# DEFAULT_BASELINE = CONFIG.DEFAULT_BASELINE


# @attach_data_session_metadata_decorator()
# @validate_call(config={"arbitrary_types_allowed": True})
# def twod_grid_map(
#     detectors: list[StandardReadable],
#     arg1: list[int],
#     arg2: list[int],
#     axes1: Motor = inject("base.x"),  # noqa
#     axes2: Motor = inject("base.y"),  # noqa
# ) -> MsgGenerator:
#     grid = Line(axes1, arg1[0], arg1[1], arg1[2]) * ~Line(
#         axes2, arg2[0], arg2[1], arg2[2]
#     )
#     # spec = Fly(0.4 @ grid) & Circle("x", "y", 1.0, 2.8, radius=0.5)
#     stack = grid.calculate()

#     stack[0].axes()  # ['y', 'x']

#     path = Path(stack)
#     chunk = path.consume(4096)  # you can't have any more than 4096 lines on a PandA

#     LOGGER.info(len(stack[0]))  # 44
#     LOGGER.info(chunk.midpoints)  # {'x': <ndarray len=10>, 'y': <ndarray len=10>}
#     LOGGER.info(chunk.upper)  # bounds are same dimensionality as positions
#     LOGGER.info(chunk.duration)  # duration of each frame

#     yield from scanspec.spec_scan(set(detectors), grid)
