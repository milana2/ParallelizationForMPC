from enum import Enum

from . import motion, mp_spdz
from ..loop_linear_code import Function
from ..type_analysis import TypeEnv
from ..util import assert_never


class Backend(Enum):
    MOTION = "MOTION"
    MP_SPDZ = "MP-SPDZ"

    def __str__(self) -> str:
        return self.value

    def render_function(
        self, func: Function, type_env: TypeEnv, ran_vectorization: bool
    ) -> str:
        if self == Backend.MOTION:
            return motion.render_function(func, type_env, ran_vectorization)
        elif self == Backend.MP_SPDZ:
            return mp_spdz.render_function(func, type_env, ran_vectorization)
        else:
            assert_never(self)

    def render_application(
        self,
        func: Function,
        type_env: TypeEnv,
        params: dict[str, str],
        ran_vectorization: bool,
    ) -> None:
        if self == Backend.MOTION:
            return motion.render_application(func, type_env, params, ran_vectorization)
        elif self == Backend.MP_SPDZ:
            return mp_spdz.render_application(func, type_env, params, ran_vectorization)
        else:
            assert_never(self)

    def valid_protocols(self) -> list[str]:
        if self == Backend.MOTION:
            return motion.VALID_PROTOCOLS
        elif self == Backend.MP_SPDZ:
            return []
        else:
            assert_never(self)
