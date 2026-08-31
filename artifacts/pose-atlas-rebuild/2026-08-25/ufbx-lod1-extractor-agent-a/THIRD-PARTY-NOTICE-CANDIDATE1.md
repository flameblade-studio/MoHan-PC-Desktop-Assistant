# Candidate-1 offline optimizer dependency notice

- PyTorch `2.12.1+cu130`: BSD-style license; used for offline Adam/autograd and TorchScript oracle comparison only. It is not required by the ufbx-only reconstruction path.
- NumPy: BSD-3-Clause; used for offline numeric arrays and verification.
- SciPy `1.18.0`: BSD-3-Clause; used for bounded least-squares refinement after the PyTorch Adam warm start.
- Pillow: HPND; used only to render the evidence PNG.
- ufbx `v0.23.0` commit `fcc5d6ba444cfd3eb80677dba5e37e493941abe5`: project selects Alternative A MIT; used by the reconstruction calculator.

The reconstruction contract is ufbx base vertices plus the first 20 blend-shape offsets and the saved coefficients, followed by the separately saved uniform scale.
