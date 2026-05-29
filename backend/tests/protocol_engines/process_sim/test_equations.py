# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for EquationSet — ODE and algebraic equation solving."""


from app.protocol_engines.process_sim.equations import Equation, EquationSet
from app.protocol_engines.process_sim.variables import ProcessVariable


class TestEquationSet:
    """Test equation evaluation and ODE integration."""

    def test_algebraic_direct_assignment(self):
        """Algebraic equation sets target directly."""
        variables = {
            "a": ProcessVariable(name="a", initial_value=10.0, time_constant_s=0.0, noise_std=0.0),
            "b": ProcessVariable(name="b", initial_value=0.0, time_constant_s=0.0, noise_std=0.0),
        }
        equations = EquationSet([
            Equation(target="b", kind="algebraic", func=lambda v: v["a"] * 2),
        ])

        equations.step(variables, 1.0)
        assert variables["b"].value == 20.0

    def test_ode_forward_euler(self):
        """ODE integrates via forward Euler."""
        variables = {
            "x": ProcessVariable(
                name="x", initial_value=100.0, time_constant_s=0.0,
                noise_std=0.0, min_value=-1e6, max_value=1e6,
            ),
        }
        # dx/dt = -10 (constant drain of 10 per second)
        equations = EquationSet([
            Equation(target="x", kind="ode", func=lambda v: -10.0),
        ])

        # After 1 second at rate -10: x should be 90
        equations.step(variables, 1.0)
        assert abs(variables["x"].value - 90.0) < 0.01

        # After another second: x should be 80
        equations.step(variables, 1.0)
        assert abs(variables["x"].value - 80.0) < 0.01

    def test_ode_tank_draining(self):
        """Tank draining model: d(level)/dt = -k * level.

        Analytical solution: level(t) = level_0 * exp(-k * t).
        After 10 steps of 0.1s with k=1: level ~ 100 * exp(-1) ≈ 36.8.
        Forward Euler has some error, but should be within ~5%.
        """
        variables = {
            "level": ProcessVariable(
                name="level", initial_value=100.0, time_constant_s=0.0,
                noise_std=0.0, min_value=0.0, max_value=1000.0,
            ),
        }
        equations = EquationSet([
            Equation(target="level", kind="ode", func=lambda v: -1.0 * v["level"]),
        ])

        # 10 steps of 0.1s = 1 second total
        for _ in range(10):
            equations.step(variables, 0.1)

        # Analytical: 100 * exp(-1) ≈ 36.79
        import math
        analytical = 100.0 * math.exp(-1.0)
        assert abs(variables["level"].value - analytical) < 5.0

    def test_algebraic_before_ode(self):
        """Algebraic equations run first, so ODE can use their results."""
        variables = {
            "speed": ProcessVariable(name="speed", initial_value=100.0, time_constant_s=0.0, noise_std=0.0),
            "power": ProcessVariable(name="power", initial_value=0.0, time_constant_s=0.0, noise_std=0.0),
            "energy": ProcessVariable(
                name="energy", initial_value=0.0, time_constant_s=0.0,
                noise_std=0.0, min_value=-1e6, max_value=1e6,
            ),
        }
        equations = EquationSet([
            # Algebraic: power = speed * 0.5
            Equation(target="power", kind="algebraic", func=lambda v: v["speed"] * 0.5),
            # ODE: d(energy)/dt = power (integration of power over time)
            Equation(target="energy", kind="ode", func=lambda v: v["power"]),
        ])

        equations.step(variables, 1.0)
        # power should be 50 (algebraic)
        assert abs(variables["power"].value - 50.0) < 0.01
        # energy should be 50 (ODE: 0 + 50 * 1.0)
        assert abs(variables["energy"].value - 50.0) < 0.01

    def test_zero_dt_noop(self):
        variables = {
            "x": ProcessVariable(name="x", initial_value=10.0, time_constant_s=0.0, noise_std=0.0),
        }
        equations = EquationSet([
            Equation(target="x", kind="ode", func=lambda v: 100.0),
        ])
        equations.step(variables, 0.0)
        assert variables["x"].value == 10.0

    def test_empty_equation_set(self):
        """Empty equation set just steps variables."""
        variables = {
            "x": ProcessVariable(
                name="x", initial_value=0.0, time_constant_s=0.0, noise_std=0.0,
            ),
        }
        variables["x"].set_target(50.0)
        equations = EquationSet([])
        equations.step(variables, 1.0)
        assert variables["x"].value == 50.0
