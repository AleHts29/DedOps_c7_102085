# Práctica — Módulo 7: DevSecOps y FinOps

**Tiempo estimado:** 70 a 85 minutos
**Se entrega:** hallazgos documentados, un workflow de seguridad funcionando y un plan de FinOps
**Necesitás:** Docker corriendo y Python 3. Nada de cuentas de nube ni tarjetas.

---

## Qué vas a hacer

La práctica tiene dos mitades, igual que la clase.

**Seguridad (ejercicios 1 a 4).** Vas a escanear una aplicación que tiene fallas puestas a propósito, con cuatro herramientas distintas. Cada una encuentra cosas que las otras no ven, y ese contraste es el contenido real del ejercicio.

**Costos (ejercicio 5).** Vas a analizar el inventario de una empresa ficticia y armar un plan de ahorro priorizado.

```
   EJERCICIO 1      EJERCICIO 2      EJERCICIO 3      EJERCICIO 4      EJERCICIO 5
      SAST              SCA            IMAGEN            DAST            FINOPS
   tu código       dependencias      el contenedor     la app viva      la factura
```

> **Sobre la app insegura:** `app/app_insegura.py` tiene seis vulnerabilidades deliberadas, cada una comentada con su explicación y su arreglo. Al lado está `app/app_segura.py` con las seis corregidas. Leer los dos en paralelo es parte del ejercicio: la diferencia suele ser de una o dos líneas.

---

# Ejercicio 1 — SAST: analizar el código

**Objetivo:** ver qué encuentra un escáner leyendo el código, sin ejecutarlo.
**Tiempo:** 15 minutos

## Paso 1 — Leer la app antes de escanearla

Abrí `app/app_insegura.py` y leelo completo. Cada bloque dice qué está mal y por qué. **Intentá adivinar cuántos hallazgos va a encontrar el escáner antes de correrlo.** Anotá tu número.

## Paso 2 — Correr Semgrep

No hace falta instalar nada: corre en un contenedor.

```bash
cd practica-modulo-07

docker run --rm -v "$PWD:/src" semgrep/semgrep \
  semgrep --config=p/security-audit --config=p/secrets /src/app
```

> **En Windows con PowerShell:** cambiá `"$PWD:/src"` por `"${PWD}:/src"`.

La primera vez tarda un par de minutos porque descarga la imagen y las reglas.

## Paso 3 — Leer la salida

Semgrep imprime un bloque por hallazgo:

```
  app/app_insegura.py
     generic.secrets.security.detected-generic-api-key
        Generic API Key detected
         19┆ API_KEY = "xxxxx"
```

Cada hallazgo te da tres cosas: **la regla** que se disparó, **el archivo y la línea exacta**, y **el fragmento de código**. Esa precisión es la ventaja de SAST.

Deberías encontrar hallazgos en estas categorías:

| Categoría | Dónde está |
|---|---|
| Credenciales en el código | Las constantes `DB_PASSWORD` y `API_KEY` |
| Inyección SQL | La función `buscar_usuario` |
| Hash inseguro | La función `hashear` (MD5) |
| Inyección de comandos | La función `ping` (`shell=True`) |
| Flask en modo debug | La última línea del archivo |

## Paso 4 — Comparar con la versión corregida

```bash
docker run --rm -v "$PWD:/src" semgrep/semgrep \
  semgrep --config=p/security-audit --config=p/secrets /src/app/app_segura.py
```

Casi todos los hallazgos desaparecen. **Abrí los dos archivos lado a lado** y fijate qué cambió exactamente en cada caso: casi siempre es una línea.

## ✅ Cómo saber que salió bien

- Semgrep terminó y mostró hallazgos en `app_insegura.py`
- Podés nombrar tres hallazgos y explicar por qué cada uno es un problema
- El escaneo de `app_segura.py` devuelve muchos menos hallazgos

## ⚠️ Problemas comunes

| Error | Solución |
|---|---|
| `docker: invalid reference format` en Windows | Usá `"${PWD}:/src"` en PowerShell, o Git Bash |
| Tarda muchísimo la primera vez | Normal: descarga la imagen y el set de reglas |
| `permission denied` en Linux | Agregá tu usuario al grupo docker, o usá `sudo` |

---

# Ejercicio 2 — SCA: analizar las dependencias

**Objetivo:** descubrir que la mayor parte del riesgo no está en tu código.
**Tiempo:** 15 minutos

## Paso 1 — Mirar lo que declaraste

```bash
cat app/requirements.txt
```

Cuatro librerías, con versiones viejas a propósito.

## Paso 2 — Escanear con Trivy

```bash
docker run --rm -v "$PWD:/src" aquasec/trivy fs /src/app
```

Trivy lee `requirements.txt`, busca cada versión en bases de datos públicas de vulnerabilidades y te devuelve lo que encuentra:

```
Total: 23 (HIGH: 15, CRITICAL: 8)

┌──────────┬────────────────┬──────────┬───────────────────┬───────────────┐
│ Library  │ Vulnerability  │ Severity │ Installed Version │ Fixed Version │
├──────────┼────────────────┼──────────┼───────────────────┼───────────────┤
│ jinja2   │ CVE-2024-XXXXX │ HIGH     │ 2.11.3            │ 3.1.3         │
```

**Fijate en la columna "Fixed Version".** Esa es la diferencia entre SCA y SAST: acá no hay nada que reescribir, solo hay que actualizar un número.

## Paso 3 — Arreglarlo

Editá `app/requirements.txt` y subí las versiones:

```
flask==3.0.3
requests==2.32.3
jinja2==3.1.4
pyyaml==6.0.2
```

Volvé a escanear:

```bash
docker run --rm -v "$PWD:/src" aquasec/trivy fs /src/app
```

La cantidad de hallazgos cae drásticamente. **Capturá el antes y el después:** es parte de la entrega.

## Paso 4 — Buscar secretos en el historial de Git

Una credencial borrada del código sigue estando en los commits viejos. Por eso el escaneo de secretos mira **todo el historial**:

```bash
docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest \
  detect --source /repo --verbose --no-git
```

> El flag `--no-git` escanea los archivos tal como están. Sin ese flag, recorre todo el historial de commits, que es lo que se hace en un repositorio real.

## ✅ Cómo saber que salió bien

- Trivy encontró vulnerabilidades en las dependencias originales
- Después de actualizar, la cantidad bajó mucho
- Tenés las dos capturas

---

# Ejercicio 3 — Escanear la imagen Docker

**Objetivo:** entender que heredás las vulnerabilidades de tu imagen base.
**Tiempo:** 15 minutos

## Paso 1 — Construir y escanear

```bash
docker build -t practica:insegura app/
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image practica:insegura
```

> **En Windows:** cambiá `/var/run/docker.sock` por `//var/run/docker.sock` (dos barras al principio).

Trivy ahora escanea **dos cosas distintas**:

1. Los paquetes del sistema operativo de la imagen base (Debian, en este caso)
2. Las librerías Python instaladas adentro

La mayoría de los hallazgos vienen de la imagen base, **no de tu código**.

## Paso 2 — Cambiar la imagen base

El `Dockerfile` usa `python:3.9-slim`, que es vieja. Construí la versión corregida:

```bash
docker build -t practica:segura -f app/Dockerfile.seguro app/
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image practica:segura
```

Compará los totales. **Cambiar una línea del Dockerfile suele eliminar más vulnerabilidades que semanas de arreglar código propio.**

## Paso 3 — Ver la otra diferencia

Abrí `app/Dockerfile.seguro` y fijate en estas dos líneas:

```dockerfile
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
```

Sin eso, el proceso corre como **root dentro del contenedor**. Si alguien logra ejecutar código ahí adentro, lo hace con todos los privilegios. Es uno de los hallazgos más frecuentes en auditorías reales y se arregla con dos líneas.

## ✅ Cómo saber que salió bien

- Tenés el conteo de vulnerabilidades de las dos imágenes
- Podés explicar por qué la segunda tiene menos
- Entendés qué hace `USER appuser`

---

# Ejercicio 4 — DAST: atacar la app corriendo

**Objetivo:** ver que DAST encuentra cosas completamente distintas a SAST.
**Tiempo:** 15 minutos

## Paso 1 — Levantar la aplicación

```bash
docker run -d -p 8000:8000 --name app-insegura practica:insegura
curl http://localhost:8000/
```

Tiene que responder un JSON. Si no, mirá `docker logs app-insegura`.

## Paso 2 — Escanear con OWASP ZAP

```bash
docker run --rm --network host \
  zaproxy/zap-stable zap-baseline.py \
  -t http://localhost:8000
```

> **En Mac y Windows** `--network host` no funciona igual. Usá:
> ```bash
> docker run --rm zaproxy/zap-stable zap-baseline.py \
>   -t http://host.docker.internal:8000
> ```

El escaneo tarda unos minutos: ZAP recorre la app y le tira pruebas pasivas.

## Paso 3 — Leer el reporte

```
WARN-NEW: Content Security Policy (CSP) Header Not Set [10038]
WARN-NEW: Missing Anti-clickjacking Header [10020]
WARN-NEW: X-Content-Type-Options Header Missing [10021]

FAIL-NEW: 0   WARN-NEW: 3   PASS: 48
```

## Paso 4 — El punto del ejercicio

Poné lado a lado los hallazgos de Semgrep (ejercicio 1) y los de ZAP:

| Semgrep encontró | ZAP encontró |
|---|---|
| Contraseña en el código | Falta la cabecera CSP |
| Inyección SQL | Falta protección anti-clickjacking |
| MD5 | Falta X-Content-Type-Options |
| `shell=True` | |
| Debug activado | |

**Cero superposición.** Semgrep no tiene idea de que faltan cabeceras HTTP, porque eso no está escrito en ninguna línea de código: es una consecuencia de cómo se comporta la app. Y ZAP no tiene idea de que hay una contraseña hardcodeada, porque nunca vio el código.

Esa tabla **es el entregable principal** de la primera mitad.

## Paso 5 — Limpiar

```bash
docker stop app-insegura && docker rm app-insegura
```

## ✅ Cómo saber que salió bien

- ZAP terminó y dio un reporte con warnings
- Armaste la tabla comparativa
- Podés explicar por qué ninguna herramienta encontró lo de la otra

---

# Ejercicio 5 — FinOps: encontrar la plata

**Objetivo:** priorizar acciones de ahorro por impacto y por riesgo.
**Tiempo:** 20 minutos

## Paso 1 — Mirar el inventario

```bash
cd finops
cat inventario.csv
```

Son 14 recursos de una empresa ficticia, con su costo mensual, el tamaño asignado, el uso real medido en p95, y si son interrumpibles o apagables.

## Paso 2 — Correr la calculadora

```bash
python3 calculadora_finops.py
```

Te devuelve un informe con las tres fases de FinOps: informar, optimizar y operar.

## Paso 3 — Leer el informe con criterio

No lo tomes como una lista de tareas. Mirá tres cosas:

**La fase de informar.** Hay recursos sin etiquetar. Fijate cuánto representan y pensá: si nadie sabe de quién son, ¿quién decide si se pueden apagar?

**El orden de las acciones.** El informe las ordena por ahorro, pero al final te dice que el orden real de ejecución es otro, porque considera el **riesgo**. Apagar staging el fin de semana no rompe nada; hacer rightsizing de una base de datos de producción sí puede romper algo.

**El caso de `k8s-prod-nodo-3`.** Tiene el mismo tamaño que sus dos hermanos pero usa una fracción de la CPU. Eso es raro: puede ser un nodo mal balanceado, o uno que quedó fuera del pool. Antes de achicarlo, hay que investigar por qué está así.

> **Ojo con el número final.** El ahorro que calcula ronda el 55 %, y eso es optimista a propósito: los datos están armados para que haya mucho que encontrar. En un entorno real que ya tuvo algo de atención, un 15 a 25 % es un resultado muy bueno.

## Paso 4 — Armar tu plan

Creá un archivo `finops/plan.md` con:

1. **Las tres acciones que harías primero**, en orden, justificando por ahorro **y** por riesgo.
2. **El ahorro mensual estimado** de cada una, con la cuenta hecha.
3. **Qué métrica usarías para verificar** que cada acción funcionó y no rompió nada.
4. **Una acción que el informe propone y vos NO harías**, explicando por qué.

> El punto 4 es el más importante. La calculadora es tonta: aplica fórmulas. Vos tenés que mirar el contexto. Por ejemplo, ¿harías rightsizing de `rds-prod-principal` con un solo dato de p95, sin saber si hay cierres de mes?

## Paso 5 — Probar con otros datos

Editá `inventario.csv`, agregá recursos o cambiá los números, y volvé a correr la calculadora. Es la forma más rápida de entender qué mueve la aguja.

## ✅ Cómo saber que salió bien

- La calculadora corrió y leíste el informe completo
- Tenés `plan.md` con las cuatro secciones
- Podés justificar por qué tu orden no es el mismo que el del informe

---

# Ejercicio 6 — Automatizarlo todo (opcional pero recomendado)

**Tiempo:** 10 minutos

Hasta acá corriste todo a mano. Ahora dejalo corriendo solo.

Copiá `.github/workflows/devsecops.yml` a tu repositorio del curso, commiteá y pusheá:

```bash
git checkout -b sec/devsecops
git add .github/workflows/devsecops.yml
git commit -m "ci: agrego pipeline de seguridad"
git push origin sec/devsecops
```

Abrí el pull request y mirá la pestaña **Actions**. Vas a ver cinco jobs: cuatro corriendo en paralelo (SAST, dependencias, imagen, infraestructura) y el quinto (DAST) esperando a que termine el de la imagen.

**Fijate en los `continue-on-error: true` y `soft_fail: true` del archivo.** Están puestos a propósito: al introducir escáneres en un proyecto que ya existe, primero mirás, después bloqueás. Si bloqueás desde el día uno, el equipo no puede trabajar y alguien desactiva el pipeline en una semana.

## Bonus — Escanear el Terraform

```bash
docker run --rm -v "$PWD:/tf" bridgecrew/checkov -d /tf/terraform
```

`terraform/main.tf` tiene cuatro problemas a propósito: un bucket público, uno sin cifrar, SSH abierto a internet y una instancia sobredimensionada sin etiquetas. Compará con `main_seguro.tf.ejemplo`.

**Fijate en el último:** la instancia `m5.4xlarge` sin tags no es un hallazgo de seguridad, es uno de FinOps. Y lo detecta la misma herramienta, en el mismo pipeline. Esa es la idea que une las dos mitades de la clase.

---

# Entrega

Creá `modulo-07/` en tu repositorio:

```
modulo-07/
├── hallazgos.md          ← la tabla comparativa + los hallazgos de cada herramienta
├── plan.md               ← el plan de FinOps del ejercicio 5
└── evidencias/
    ├── 01-semgrep.png
    ├── 02-trivy-antes.png
    ├── 03-trivy-despues.png
    ├── 04-zap.png
    └── 05-finops.png
```

En `hallazgos.md`:

1. La tabla comparativa SAST vs DAST del ejercicio 4
2. Tres hallazgos de Semgrep, explicando con tus palabras por qué cada uno es peligroso
3. Cuántas vulnerabilidades tenían las dependencias antes y después de actualizarlas
4. Cuántas tenía cada imagen Docker, y a qué atribuís la diferencia
5. Una respuesta de media carilla: **si tuvieras que elegir UNA sola de las cuatro herramientas para un equipo que arranca de cero, ¿cuál elegirías y por qué?**

> La pregunta 5 no tiene respuesta correcta. Lo que se evalúa es el criterio: hay buenos argumentos para SCA (es donde está la mayor parte del riesgo y es lo más barato de arreglar) y para el escaneo de secretos (una credencial filtrada es un incidente inmediato).

## Cómo se evalúa

| Criterio | Peso |
|---|---|
| Ejercicios 1 a 4: los cuatro escaneos corridos con evidencia | 30 % |
| La tabla comparativa SAST vs DAST, bien justificada | 20 % |
| Ejercicio 5: plan de FinOps con cuentas y criterio de riesgo | 30 % |
| Las cinco preguntas de `hallazgos.md` | 20 % |
| Ejercicio 6: workflow funcionando en GitHub Actions | Bonus +10 % |

---

# Si querés ir más lejos

- **Arreglá los seis hallazgos vos mismo** en una copia de `app_insegura.py`, sin mirar `app_segura.py`, y después compará.
- **Hacé que el pipeline bloquee de verdad:** sacá los `continue-on-error` y poné `exit-code: '1'` en Trivy. Mirá cuántas veces se rompe en una semana de trabajo normal.
- **Probá el modo full de ZAP** (`zap-full-scan.py`): tarda mucho más y encuentra bastante más.
- **Sumá Dependabot** al repositorio: GitHub te abre pull requests solo cuando aparece una vulnerabilidad en una dependencia.
- **Agregá una política de etiquetas obligatorias** en Checkov con una regla propia, y hacé que el pipeline rechace cualquier recurso de Terraform sin `CentroCosto`.
