from dataclasses import dataclass
import numpy as np
from lib.ml.layer.actual_layer import (
    ActivationLayer,
    BiasedWeightLayer,
    CompositeLayer,
    Layer,
    ReshapeLayer,
    WeightLayer,
)
from lib.ml.optimizer.nn_optimizer import (
    LayerSupplier,
    NeuralNetOptimizer,
    OptimalResult,
)
from lib.ml.util.loss_function import LossFunction
from lib.ml.util.types import ArrayLike, ShapeLike


class GradientDescentOptimizer(NeuralNetOptimizer):
    __learning_rate: float
    __momentum: float
    __target: Layer
    __velocities: dict[int, dict[str, ArrayLike]]

    def __init__(self, learning_rate: float, momentum: float = 0) -> None:
        self.__learning_rate = learning_rate
        self.__momentum = momentum

    def prepare(self, params_supplier: LayerSupplier) -> None:
        self.__target = params_supplier()
        self.__init_velocity(self.__target)

    def optimize(
        self, epoch: int, x: ArrayLike, y_true: ArrayLike, loss: LossFunction
    ) -> OptimalResult:
        loss = 0

        match self.__target:
            case CompositeLayer(values):
                loss = self.__optimize_deep(values, x, y_true, loss)
            case it:
                loss = self.__optimize_deep([it], x, y_true, loss)

        return OptimalResult(self.__target, loss)

    def __optimize_deep(
        self,
        layers: list[Layer],
        x: ArrayLike,
        y_true: ArrayLike,
        loss_fun: LossFunction,
    ) -> float:
        def optimize_recursively(
            layer_num: int, a_prev: ArrayLike
        ) -> tuple[ArrayLike, float]:
            if layer_num >= len(layers):
                da = loss_fun.apply_derivative(y_true, a_prev)
                loss = loss_fun.apply(y_true, a_prev)

                return da, loss

            match layers[layer_num + 1]:
                case BiasedWeightLayer() as it:
                    z = np.dot(it.weight, a_prev) + it.bias
                    m = a_prev.shape[1]

                    dz, loss = optimize_recursively(layer_num + 1, z)

                    dw = np.dot(dz, a_prev.T) / m
                    db = np.mean(dz, axis=1, keepdims=True)
                    da = np.dot(it.weight.T, dz)

                    velocity = self.__velocities[layer_num]

                    velocity["dw"] = self.__calculate_velocity(dw, velocity["dw"])
                    velocity["db"] = self.__calculate_velocity(db, velocity["db"])

                    it.weight -= self.__learning_rate * velocity["dw"]
                    it.bias -= self.__learning_rate * velocity["db"]

                    return da, loss
                case WeightLayer() as it:
                    z = np.dot(it.weight, a_prev)
                    m = a_prev.shape[1]

                    dz, loss = optimize_recursively(layer_num + 1, z)

                    dw = np.dot(dz, a_prev.T) / m
                    da = np.dot(it.weight.T, dz)

                    velocity = self.__velocities[layer_num]

                    velocity["dw"] = self.__calculate_velocity(dw, velocity["dw"])

                    it.weight -= self.__learning_rate * velocity["dw"]

                    return da, loss
                case ActivationLayer(fun):
                    a = fun.apply(a_prev)

                    da_next, loss = optimize_recursively(layer_num + 1, a)

                    dz = da_next * fun.apply_derivative(z)

                    return dz, loss
                case ReshapeLayer() as it:
                    a = it.apply(a_prev)

                    da_next, loss = optimize_recursively(layer_num + 1, a)

                    dz = it.apply(da_next)

                    return dz, loss

        _, loss = optimize_recursively(0, x)

        return loss

    def __init_velocity(self, layer: Layer, id: int = 0):
        match layer:
            case CompositeLayer(values):
                for i in range(len(values)):
                    self.__init_velocity(values[i], i)
            case BiasedWeightLayer(weight, bias):
                self.__velocities[id] = {
                    "dw": np.zeros(weight.shape),
                    "db": np.zeros(bias.shape),
                }
            case WeightLayer(weight):
                self.__velocities[id] = {
                    "dw": np.zeros(weight.shape),
                }

    def __calculate_velocity(self, d: ArrayLike, d_velocity: ArrayLike) -> ArrayLike:
        return self.__momentum * d_velocity + (1 - self.__momentum) * d
