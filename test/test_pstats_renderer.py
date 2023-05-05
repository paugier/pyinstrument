import time
from pstats import Stats

import pytest

from pyinstrument import Profiler
from pyinstrument.renderers import PstatsRenderer
from test.fake_time_util import fake_time


def a():
    b()
    c()


def b():
    d()


def c():
    d()


def d():
    e()


def e():
    time.sleep(1)


@pytest.fixture(scope="module")
def profiler_session():
    with fake_time():
        profiler = Profiler()
        profiler.start()

        a()

        profiler.stop()
        return profiler.last_session


def test_pstats_renderer(profiler_session, tmp_path):
    fname = tmp_path / "test.prof"
    prof = PstatsRenderer().render(profiler_session)
    with open(fname, "w", encoding="utf-8", errors="surrogateescape") as fid:
        fid.write(prof)
    stats = Stats(str(fname))
    # Sanity check
    assert stats.total_tt > 0  # type: ignore
    # The graph is
    # a() -> b() -> d() -> e() -> time.sleep()
    #    \-> c() /
    # so make sure d has callers of b, c, and that the times make sense
    d = [k for k in stats.stats.keys() if 'd' in k]
    assert len(d) == 1
    val = stats.stats[d[0]]
    d_ttime = val[3]
    b = [k for k in stats.stats.keys() if 'b' in k]
    c = [k for k in stats.stats.keys() if 'c' in k]
    assert len(b) == 1
    assert len(c) == 1
    b_ttime = val[4][b[0]][3]
    c_ttime = val[4][c[0]][3]
    assert b_ttime - c_ttime == pytest.approx(0)
    assert b_ttime + c_ttime == pytest.approx(d_ttime)
