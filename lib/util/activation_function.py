from abc import ABC
import numpy as np

from lib.util.types import ArrayLike


class ActivationFunction(ABC):

    def apply(self, z: ArrayLike) -> ArrayLike:
        pass

    def apply_derivative(self, z: ArrayLike) -> ArrayLike:
        pass


class Linear(ActivationFunction):

    def apply(self, z: ArrayLike) -> ArrayLike:
        return z

    def apply_derivative(self, z: ArrayLike) -> ArrayLike:
        return np.ones(z.shape)


class Relu(ActivationFunction):

    def apply(self, z: ArrayLike) -> ArrayLike:
        return (z > 0) * z

    def apply_derivative(self, z: ArrayLike) -> ArrayLike:
        return z > 0


LINEAR_ACTIVATION = Linear()
RELU_ACTIVATION = Relu()
