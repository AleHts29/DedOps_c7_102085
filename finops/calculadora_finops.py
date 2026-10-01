#!/usr/bin/env python3
"""
calculadora_finops.py — Práctica del Módulo 7

Toma el inventario de recursos de inventario.csv y calcula:
  · cuánto se gasta hoy
  · cuánto se gastaría aplicando cada estrategia de FinOps
  · el ahorro de cada acción, ordenado por impacto

No necesita cuenta de nube ni credenciales: trabaja sobre un CSV.
La lógica es la misma que usarías con datos reales de facturación.

Uso:
    python3 calculadora_finops.py
    python3 calculadora_finops.py --csv mi_inventario.csv
"""
import argparse
import csv
import sys

# Horas de un mes, usando 30 días. Es la convención del módulo 6.
HORAS_MES = 30 * 24          # 720
# Un ambiente que solo corre de lunes a viernes de 8 a 20:
# 5 días × 12 horas × ~4,3 semanas = 258 horas al mes.
HORAS_LABORALES_MES = 5 * 12 * 4.3

# Descuento típico de las instancias spot (60-90 %). Usamos uno conservador.
DESCUENTO_SPOT = 0.70


def cargar(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def costo_actual(r):
    return float(r["costo_mensual_usd"])


def ahorro_apagado(r):
    """Apagar fuera de horario laboral lo que no es producción."""
    if r["ambiente"] == "produccion":
        return 0.0
    if r["apagable"].strip().lower() != "si":
        return 0.0
    proporcion = HORAS_LABORALES_MES / HORAS_MES
    return costo_actual(r) * (1 - proporcion)


def ahorro_rightsizing(r):
    """
    Si el uso p95 es muy inferior a lo asignado, se puede bajar de tamaño.
    Dejamos un colchón: nunca ajustamos por debajo del p95 + 30 %.
    """
    asignado = float(r["vcpu_asignadas"])
    usado = float(r["vcpu_p95"])
    if asignado <= 0:
        return 0.0
    objetivo = min(asignado, max(1.0, usado * 1.3))
    if objetivo >= asignado * 0.95:
        return 0.0          # ya está bien dimensionado
    proporcion_nueva = objetivo / asignado
    return costo_actual(r) * (1 - proporcion_nueva)


def ahorro_spot(r):
    """Solo aplica a cargas interrumpibles."""
    if r["interrumpible"].strip().lower() != "si":
        return 0.0
    return costo_actual(r) * DESCUENTO_SPOT


def sin_etiquetar(r):
    return not r["proyecto"].strip() or not r["equipo"].strip()


def plata(x):
    return f"${x:>9,.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="inventario.csv")
    args = ap.parse_args()

    try:
        recursos = cargar(args.csv)
    except FileNotFoundError:
        print(f"No encontré {args.csv}. Corré el script desde la carpeta finops/.")
        sys.exit(1)

    total = sum(costo_actual(r) for r in recursos)

    print("=" * 74)
    print("INFORME FINOPS".center(74))
    print("=" * 74)
    print(f"\nGasto mensual actual: {plata(total)}   ({len(recursos)} recursos)\n")

    # ── Fase 1: INFORMAR ─────────────────────────────────────
    print("-" * 74)
    print("1. INFORMAR — ¿sabemos de quién es cada peso?")
    print("-" * 74)
    huerfanos = [r for r in recursos if sin_etiquetar(r)]
    costo_huerfanos = sum(costo_actual(r) for r in huerfanos)
    if huerfanos:
        print(f"\n  {len(huerfanos)} recursos SIN ETIQUETAR: {plata(costo_huerfanos)} al mes")
        print(f"  Es el {costo_huerfanos / total * 100:.1f}% del gasto que nadie puede explicar.\n")
        for r in huerfanos:
            print(f"    · {r['nombre']:<24} {plata(costo_actual(r))}")
    else:
        print("\n  Todo etiquetado. Se puede pasar a optimizar.")

    print("\n  Gasto por ambiente:")
    por_ambiente = {}
    for r in recursos:
        por_ambiente[r["ambiente"]] = por_ambiente.get(r["ambiente"], 0) + costo_actual(r)
    for amb, c in sorted(por_ambiente.items(), key=lambda x: -x[1]):
        barra = "█" * int(c / total * 40)
        print(f"    {amb:<14} {plata(c)}  {barra}")

    # ── Fase 2: OPTIMIZAR ────────────────────────────────────
    print("\n" + "-" * 74)
    print("2. OPTIMIZAR — ¿dónde está la plata?")
    print("-" * 74)

    acciones = []
    for r in recursos:
        for nombre, fn in (
            ("Apagar fuera de horario", ahorro_apagado),
            ("Rightsizing", ahorro_rightsizing),
            ("Pasar a spot", ahorro_spot),
        ):
            a = fn(r)
            if a > 1:
                acciones.append((a, nombre, r["nombre"], r["ambiente"]))

    acciones.sort(reverse=True)

    print(f"\n  {'AHORRO/MES':>12}  {'ACCIÓN':<26} {'RECURSO':<22} AMBIENTE")
    print("  " + "-" * 70)
    for a, accion, recurso, amb in acciones:
        print(f"  {plata(a)}  {accion:<26} {recurso:<22} {amb}")

    # Para no sumar dos veces el mismo recurso, nos quedamos con la
    # mejor acción de cada uno.
    mejor_por_recurso = {}
    for a, accion, recurso, _ in acciones:
        if recurso not in mejor_por_recurso or a > mejor_por_recurso[recurso][0]:
            mejor_por_recurso[recurso] = (a, accion)

    ahorro_total = sum(a for a, _ in mejor_por_recurso.values())

    print("\n" + "=" * 74)
    print(f"  Gasto actual:            {plata(total)}")
    print(f"  Ahorro potencial:        {plata(ahorro_total)}   "
          f"({ahorro_total / total * 100:.1f}% del total)")
    print(f"  Gasto optimizado:        {plata(total - ahorro_total)}")
    print(f"  Ahorro anual estimado:   {plata(ahorro_total * 12)}")
    print("=" * 74)

    # ── Fase 3: OPERAR ───────────────────────────────────────
    print("\n3. OPERAR — qué hacer el lunes a la mañana\n")
    print("  Las acciones están ordenadas por ahorro, pero el orden real")
    print("  de ejecución tiene que considerar también el riesgo:\n")
    print("   1. Etiquetar todo lo que falta (no ahorra solo, pero habilita el resto)")
    print("   2. Apagar ambientes de no-producción fuera de horario (riesgo nulo)")
    print("   3. Mover cargas interrumpibles a spot (riesgo bajo)")
    print("   4. Rightsizing, de a un escalón y mirando el monitoreo (riesgo medio)\n")


if __name__ == "__main__":
    main()
