# Formula OCR (GPU service)

Each line the CPU OCR read that looks like a formula is cropped and read again by the formula-OCR model on the GPU service; the LaTeX is kept (appended to the region text the tutor reads) only when it adds something and shares most letters and digits with the OCR text. Made by `backend/scripts/eval_latex.py`.

27 formula lines sent, 14 LaTeX kept; GPU time per image 1.0-18.4 s (in the background, while the CPU stages run).

| image | CPU OCR text | LaTeX from the GPU | kept |
|---|---|---|---|
| samples/synthetic/clean/formulas_kinematics.png | `v =u + at` | `v=u+at` | no |
| samples/synthetic/clean/formulas_kinematics.png | `S = ut + 12at2` | `s=ut+\frac{1}{2}at^2` | yes |
| samples/synthetic/clean/formulas_kinematics.png | `v2 = u2 + 2as` | `v^2=u^2+2as` | yes |
| samples/synthetic/clean/formulas_kinematics.png | `F = ma` | `F=ma` | no |
| samples/synthetic/photo/formulas_kinematics.jpg | `v=u+at` | `v=u+at` | no |
| samples/synthetic/photo/formulas_kinematics.jpg | `s=ut+y2at²` | `s=ut+\frac{1}{2}at^2` | yes |
| samples/synthetic/photo/formulas_kinematics.jpg | `v²=u²+2as` | `v^2=u^2+2as` | yes |
| samples/synthetic/photo/formulas_kinematics.jpg | `F=ma` | `F=ma` | no |
| samples/synthetic/photo/formulas_kinematics.jpg | `Example:u=0,a=2m/s²,t=5s→v=u+at=10m/s` | `(10,10),(988,988)` | no |
| samples/synthetic/dark/formulas_kinematics.png | `v =u + at` | `v=u+at` | no |
| samples/synthetic/dark/formulas_kinematics.png | `S = ut + 12at2` | `s=ut+\frac{1}{2}at^2` | yes |
| samples/synthetic/dark/formulas_kinematics.png | `v2 = u2 + 2as` | `v^2=u^2+2as` | yes |
| samples/synthetic/dark/formulas_kinematics.png | `F = ma` | `F=ma` | no |
| backend/tests/fixtures/bullets_formula.png | `F=mxa` | `F=m\times a` | yes |
| backend/tests/fixtures/bullets_formula.png | `a = F / m` | `a=F/m` | no |
| samples/bench/images/math_kinematics_slide.png | `v =u + at` | `v=u+at` | no |
| samples/bench/images/math_kinematics_slide.png | `S = ut + 12at2` | `s=ut+\frac{1}{2}at^2` | yes |
| samples/bench/images/math_kinematics_slide.png | `v2 = u2 + 2as` | `v^2=u^2+2as` | yes |
| samples/bench/images/math_kinematics_slide.png | `F = ma` | `F=ma` | no |
| samples/bench/images/math_quadratic_roots.png | `3- -=x²--x÷ 2` | `$$\begin{array}{ll}{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\{{}}&{{}}\\` | no |
| samples/bench/images/math_unit_circle.png | `π3π4` | `\frac{\pi}{3}+\frac{\pi}{4}=\frac{7\pi}{12}` | no |
| samples/bench/images/math_unit_circle.png | `11π` | `\frac{11\pi}{6}` | yes |
| samples/bench/images/math_derivative_tangent.png | `y=f(x)` | `y=f(x)` | no |
| samples/bench/images/math_derivative_tangent.png | `y=mx+b, where rm=f'(a)` | `y=mx+b,\text{where}m=f^{\prime}(a).` | yes |
| samples/bench/images/math_ohm_internal_resistance.jpg | `Ir= 4,5 V` | `lr=4,5\,\text{V}` | yes |
| samples/bench/images/math_ohm_internal_resistance.jpg | `ε=12V` | `\epsilon=12\,\text{V}` | yes |
| samples/bench/images/math_ohm_internal_resistance.jpg | `IR= 7,5 V` | `IR=7.5\,\text{V}` | yes |
