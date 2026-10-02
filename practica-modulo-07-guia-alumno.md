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

Cuatro librerías con versiones viejas a propósito, más `markupsafe` fijada porque `jinja2` 2.11 no funciona con versiones nuevas de esa librería.

## Paso 2 — Escanear con Trivy

```bash
docker run --rm -v "$PWD:/src" aquasec/trivy fs /src/app
```

Trivy lee `requirements.txt`, busca cada versión en bases de datos públicas de vulnerabilidades y te devuelve lo que encuentra. Vas a ver una tabla parecida a esta (los números exactos cambian a medida que se publican CVEs nuevas):

```
requirements.txt (pip)
Total: 10 (UNKNOWN: 0, LOW: 1, MEDIUM: 8, HIGH: 1, CRITICAL: 0)

┌──────────┬────────────────┬──────────┬───────────────────┬───────────────┐
│ Library  │ Vulnerability  │ Severity │ Installed Version │ Fixed Version │
├──────────┼────────────────┼──────────┼───────────────────┼───────────────┤
│ flask    │ CVE-2023-30861 │ HIGH     │ 1.1.4             │ 2.3.2, 2.2.5  │
│ jinja2   │ CVE-2024-56326 │ MEDIUM   │ 2.11.3            │ 3.1.5         │
│ requests │ CVE-2024-35195 │ MEDIUM   │ 2.25.1            │ 2.32.0        │
│ ...      │                │          │                   │               │
```

> Trivy también escanea secretos por defecto, así que además va a marcar la API key de `app_insegura.py`. Eso ya lo viste en el ejercicio 1; acá concentrate en la tabla de `requirements.txt`.

**Fijate en la columna "Fixed Version".** Esa es la diferencia entre SCA y SAST: acá no hay nada que reescribir, solo hay que actualizar un número.

## Paso 3 — Arreglarlo

Editá `app/requirements.txt` y subí las versiones (la línea de `markupsafe` la podés borrar: `jinja2` 3.x trae la versión que necesita):

```
flask==3.1.3
requests==2.32.5
jinja2==3.1.6
pyyaml==6.0.2
```

> **¿Por qué no la última versión de `requests`?** La 2.33 exige Python 3.10 o superior, y el `Dockerfile` del ejercicio 3 usa Python 3.9. Por eso va a quedar **una** vulnerabilidad MEDIUM en `requests` que no se puede arreglar sin actualizar también Python. Pasa seguido en la vida real: a veces el arreglo de una dependencia te obliga a mover la imagen base.

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

> **Ojo:** en el ejercicio 2 ya corregiste `requirements.txt`, y aun así vas a ver vulnerabilidades en librerías Python. Mirá cuáles son: `pip`, `setuptools`, `wheel`, `urllib3`... **Ninguna está en tu `requirements.txt`.** Algunas vienen con la imagen base y otras son dependencias de tus dependencias (`urllib3` la trae `requests`). El escaneo de archivos (`trivy fs`) no las puede ver; solo aparecen cuando escaneás la imagen construida.

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

## Paso 4 — Filtrar lo accionable

Un reporte con cientos de vulnerabilidades **no es una lista de tareas**. Nadie arregla 450 cosas. El trabajo real es filtrar y decidir.

De todo el reporte, lo que vale la pena atacar primero es lo **grave** que **ya tiene arreglo**:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL --ignore-unfixed practica:insegura

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL --ignore-unfixed practica:segura
```

- `--severity HIGH,CRITICAL` deja afuera LOW y MEDIUM.
- `--ignore-unfixed` oculta las que todavía no tienen parche (columna **Status** distinta de `fixed`). Con esas no podés hacer nada más que aceptar el riesgo o cambiar de imagen.

Vas a ver algo parecido a esto (los números cambian día a día porque se publican CVEs nuevas):

| Imagen | Reporte completo | HIGH/CRITICAL con arreglo |
|---|---|---|
| `practica:insegura` (Python 3.9) | ~470 | ~80 |
| `practica:segura` (Python 3.12) | ~210 | ~7 |

**De cientos de hallazgos pasaste a un puñado.** Esa es la lista con la que se trabaja.

### ¿Y qué hago con cada uno?

Depende de **dónde** está la vulnerabilidad. Mirá la columna *Library* y el bloque del reporte donde aparece (sistema operativo o Python):

| Origen del hallazgo | Qué se hace | Cómo se ve en el Dockerfile |
|---|---|---|
| **Imagen base vieja** | Usar una versión más nueva | `FROM python:3.12-slim` (lo que hiciste en el Paso 2) |
| **Paquete del SO con parche disponible** | Actualizar los paquetes al construir | `RUN apt-get update && apt-get upgrade -y` |
| **Librería Python que no declaraste** (`pip`, `setuptools`, `urllib3`...) | Actualizarla o fijarla explícitamente | `RUN pip install --upgrade pip setuptools`, o sumarla a `requirements.txt` |
| **Sin parche disponible** | Aceptar el riesgo **y documentarlo** | Una línea en `.trivyignore` con el CVE y el motivo |
| **Demasiados paquetes que no usás** | Usar una imagen mínima | `distroless`, `alpine` o `chainguard`: menos paquetes, menos superficie de ataque |

## Paso 5 — Llevarlo a cero (opcional)

Abrí `app/Dockerfile.seguro` y agregá esta línea **justo después del `FROM`**. Tiene que ir antes de `USER appuser`, porque instalar paquetes requiere root:

```dockerfile
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
```

> El `rm -rf /var/lib/apt/lists/*` borra el índice de paquetes que descargó `apt-get update`. No se necesita en tiempo de ejecución y solo agranda la imagen.

Reconstruí y volvé a escanear con el filtro:

```bash
docker build -t practica:segura -f app/Dockerfile.seguro app/
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL --ignore-unfixed practica:segura
```

Las HIGH/CRITICAL con arreglo tendrían que llegar a **cero**.

### Esto no se hace una sola vez

La imagen que hoy da cero va a tener vulnerabilidades nuevas el mes que viene: **tu código no cambió, pero se descubrieron fallas nuevas en lo que ya tenías instalado.** Por eso, en un equipo real:

1. **Se pone como gate en el pipeline.** Con `--exit-code 1`, Trivy hace fallar el build si encuentra algo grave y arreglable:
   ```bash
   trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 practica:segura
   ```
2. **Se reconstruyen las imágenes periódicamente** (por ejemplo, una vez por semana), aunque no haya cambios en el código, para recoger los parches nuevos.

Lo vas a automatizar en el Ejercicio 6.

## ✅ Cómo saber que salió bien

- Tenés el conteo de vulnerabilidades de las dos imágenes
- Podés explicar por qué la segunda tiene menos
- Entendés qué hace `USER appuser`
- Filtraste el reporte y sabés cuántas vulnerabilidades son realmente accionables
- Podés decir, para un hallazgo cualquiera del reporte, qué harías con él según la tabla del Paso 4
- *(Opcional)* Llevaste la imagen segura a cero HIGH/CRITICAL con arreglo

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

Al final vas a ver algo así:

```
WARN-NEW: X-Content-Type-Options Header Missing [10021] x 1
    http://localhost:8000 (200 OK)
WARN-NEW: Server Leaks Version Information via "Server" HTTP Response Header Field [10036] x 3
    http://localhost:8000 (200 OK)
    http://localhost:8000/robots.txt (404 Not Found)
    http://localhost:8000/sitemap.xml (404 Not Found)
WARN-NEW: Content Security Policy (CSP) Header Not Set [10038] x 1
WARN-NEW: Storable and Cacheable Content [10049] x 3
WARN-NEW: Permissions Policy Header Not Set [10063] x 2
WARN-NEW: Cross-Origin-Resource-Policy Header Missing or Invalid [90004] x 1
FAIL-NEW: 0    FAIL-INPROG: 0    WARN-NEW: 6    WARN-INPROG: 0    INFO: 0    IGNORE: 0    PASS: 61
```

### Cómo se lee cada línea

```
WARN-NEW: X-Content-Type-Options Header Missing [10021] x 1
└──┬───┘  └──────────────┬──────────────────┘  └─┬─┘  └┬┘
 nivel          qué encontró                   ID de  en cuántas
                                               regla  URLs
```

- **Nivel:** `FAIL` = problema que debería frenar un deploy. `WARN` = problema a corregir, pero no bloqueante. `INFO` = solo informativo. `IGNORE` = alguien ya lo revisó y lo aceptó. `PASS` = reglas que se probaron y no encontraron nada.
- **`-NEW` / `-INPROG`:** `NEW` es un hallazgo nuevo. `INPROG` es uno que ya se sabe y está en proceso de arreglo (se marca con un archivo de reglas, lo ves en el Paso 5).
- **ID entre corchetes:** buscalo en `https://www.zaproxy.org/docs/alerts/<ID>/` (por ejemplo, `.../alerts/10021/`) y vas a ver la explicación completa y cómo se arregla.
- **Las URLs de abajo:** dónde lo vio. `robots.txt` y `sitemap.xml` dan 404 porque ZAP siempre las prueba, existan o no.

> **"What's next: Debug this container error with Gordon"**: no es un error. ZAP termina con **código de salida 2** cuando hay warnings (0 = todo bien, 1 = hay FAIL, 2 = hay WARN), y Docker Desktop interpreta cualquier código distinto de 0 como error. En un pipeline, ese código es el que decide si el build pasa o no.

### Qué significa cada hallazgo

Todos tienen algo en común: **no son bugs del código, son cabeceras HTTP que la app no manda.** Las cabeceras son instrucciones que el servidor le da al navegador sobre cómo tratar la respuesta. Si no están, el navegador usa su comportamiento por defecto, que es el más permisivo.

| ID | Hallazgo | Qué significa | Riesgo real |
|---|---|---|---|
| 10021 | X-Content-Type-Options Header Missing | El navegador puede "adivinar" el tipo de archivo en vez de respetar el `Content-Type`. Un archivo subido como imagen podría terminar ejecutándose como script. | Bajo |
| 10036 | Server Leaks Version Information | La respuesta incluye `Server: Werkzeug/3.x Python/3.9`. Le estás diciendo a un atacante exactamente qué versión usás, para que busque CVEs de esa versión. | Bajo |
| 10038 | CSP Header Not Set | No hay *Content Security Policy*: el navegador va a cargar scripts de cualquier origen. Es la principal defensa contra XSS. | Medio |
| 10049 | Storable and Cacheable Content | La respuesta puede quedar guardada en cachés intermedios (proxies, CDN). Grave si la respuesta tiene datos de un usuario; irrelevante si es pública. | Informativo |
| 10063 | Permissions Policy Header Not Set | No se restringe el acceso a cámara, micrófono, geolocalización, etc. desde la página. | Bajo |
| 90004 | Cross-Origin-Resource-Policy Missing | Otros sitios pueden incrustar tus respuestas. Relacionado con ataques tipo Spectre que leen memoria entre orígenes. | Bajo |

### Lo que ZAP **no** encontró

La app tiene una inyección SQL en `/usuario` y una inyección de comandos en `/ping`, y ZAP no las vio. Hay dos motivos:

1. **`zap-baseline` es un escaneo pasivo**: mira las respuestas pero no manda ataques. Para eso existe `zap-full-scan.py` (activo), que tarda mucho más y **solo se corre contra entornos de prueba**, nunca contra producción.
2. **ZAP solo prueba lo que encuentra.** Recorre la app siguiendo links, y `/usuario` o `/ping` no están linkeados desde ningún lado. En una API real se le pasa la especificación OpenAPI con `zap-api-scan.py` para que conozca todas las rutas.

## Paso 4 — El punto del ejercicio

Poné lado a lado los hallazgos de Semgrep (ejercicio 1) y los de ZAP:

| Semgrep encontró | ZAP encontró |
|---|---|
| API key hardcodeada | Faltan cabeceras de seguridad (CSP, X-Content-Type-Options, Permissions-Policy, CORP) |
| `shell=True` (inyección de comandos) | El servidor expone su versión |
| Flask con `debug=True` | Respuestas cacheables |
| App escuchando en `0.0.0.0` | |

**Cero superposición.** Semgrep no tiene idea de que faltan cabeceras HTTP, porque eso no está escrito en ninguna línea de código: es una consecuencia de cómo se comporta la app. Y ZAP no tiene idea de que hay una contraseña hardcodeada, porque nunca vio el código.

Y fijate en lo que **ninguno de los dos encontró**: la inyección SQL, el MD5, la `DB_PASSWORD` y el endpoint `/debug` que expone variables de entorno. Están comentados en `app_insegura.py`, pero ninguna herramienta los marcó. **Las herramientas automáticas reducen el riesgo, no lo eliminan.** Por eso se combinan entre sí y con revisión de código hecha por personas.

## Paso 5 — Qué se hace con estos hallazgos

### Cómo se corrigen

**1. Las cabeceras (10021, 10038, 10063, 90004).** Se agregan en todas las respuestas. En Flask alcanza con una función que corre después de cada request:

```python
@app.after_request
def cabeceras_de_seguridad(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; form-action 'none'"
    resp.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    resp.headers["Cache-Control"] = "no-store"
    return resp
```

> Esta CSP es muy estricta porque la app es una API que solo devuelve JSON. Una app con HTML, CSS y JavaScript necesita una política que permita cargar sus propios recursos (por ejemplo, `default-src 'self'`). Una CSP mal armada rompe el sitio, por eso se prueba antes en modo `Content-Security-Policy-Report-Only`.

En la práctica, muchas veces estas cabeceras **no se ponen en la aplicación sino en el proxy** que está adelante (Nginx, un Ingress de Kubernetes, un balanceador o un CDN). Así se configuran una sola vez para todas las aplicaciones.

**2. La versión del servidor (10036).** El `Werkzeug/3.x` aparece porque la app corre con el servidor de desarrollo de Flask, que **no se debe usar en producción**. Con un servidor de producción como `gunicorn` la cabecera queda solo como `Server: gunicorn`, sin versión:

```dockerfile
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app_segura:app"]
```

(Hay que agregar `gunicorn` a `requirements.txt`.) Si hay un proxy adelante, también se puede ocultar ahí.

**3. El contenido cacheable (10049).** Es informativo: ZAP lo reporta **siempre**, para que alguien decida. Si la respuesta tuviera datos de un usuario, se agrega `Cache-Control: no-store` (ya está en el ejemplo de arriba). Ojo: aun así ZAP sigue mostrando la regla, ahora como *"Non-Storable Content"*, porque solo te informa cómo quedó configurado. Por eso se **acepta** y se documenta (ver más abajo).

Con los cambios 1 y 2, ZAP pasa de 6 warnings a 1 (el 10049). Con el archivo de reglas del final, llega a 0.

### A quién se le informa

Cada hallazgo tiene un dueño según **dónde se arregla**:

| Hallazgo | Se le asigna a | Por qué |
|---|---|---|
| Cabeceras de seguridad | **Equipo de desarrollo** de la app, o **plataforma/SRE** si se ponen en el proxy | Es configuración de la respuesta HTTP |
| Versión del servidor | **Plataforma/SRE** | Es cómo se despliega y sirve la app |
| Contenido cacheable | **Equipo de desarrollo** | Solo ellos saben si la respuesta tiene datos sensibles |
| Decidir qué se acepta y qué bloquea | **Equipo de seguridad** (AppSec) | Define la política y aprueba excepciones |

**Cómo se reporta:** con un ticket en el backlog del equipo dueño, no con un mail ni un mensaje suelto. El ticket lleva el ID de la regla, las URLs afectadas, la severidad y el link a la documentación de ZAP. Estos hallazgos son de severidad baja: van a la planificación normal del equipo. **No es un incidente de seguridad**, porque nadie explotó nada. Un `FAIL` o algo crítico en producción, en cambio, sigue el proceso de incidentes de la empresa y se avisa al equipo de seguridad de inmediato.

### Cómo se deja registrada la decisión

Lo que se acepta no se "ignora en silencio": se documenta en un archivo de reglas que vive en el repositorio. Creá `zap-rules.tsv` en la raíz de la práctica (los campos van separados por **tabulación**, no por espacios):

```
10049	IGNORE	(Storable and Cacheable Content) La API no devuelve datos de usuarios
10036	FAIL	(Server Leaks Version Information)
```

Y correlo montando la carpeta:

```bash
docker run --rm -v "$PWD:/zap/wrk" zaproxy/zap-stable zap-baseline.py \
  -t http://host.docker.internal:8000 -c zap-rules.tsv
```

Cada línea dice qué hacer con una regla: `IGNORE` (aceptado), `WARN` (avisar), `FAIL` (bloquear el pipeline). En el ejemplo, el 10049 queda aceptado con su justificación, y el 10036 pasa a bloquear: si alguien vuelve a desplegar con el servidor de desarrollo, el build se rompe. Así, la decisión queda en Git, con autor, fecha y motivo.

Esa tabla **es el entregable principal** de la primera mitad.

## Paso 6 — Limpiar

```bash
docker stop app-insegura && docker rm app-insegura
```

## ✅ Cómo saber que salió bien

- ZAP terminó y dio un reporte con warnings
- Armaste la tabla comparativa
- Podés explicar por qué ninguna herramienta encontró lo de la otra
- Sabés leer una línea del reporte de ZAP (nivel, ID de regla, URLs)
- Para cada warning, sabés cómo se corrige y a qué equipo se le asigna
- *(Opcional)* Creaste `zap-rules.tsv` y viste el resultado cambiar a `IGNORE`

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

**Tiempo:** 30 minutos

Hasta acá corriste todo a mano. Ahora dejalo corriendo solo: cada vez que alguien abra un pull request, GitHub Actions va a correr los cinco escaneos automáticamente, en máquinas de GitHub, sin que tengas que tipear nada.

**Necesitás:** una cuenta de GitHub y `git` instalado. No hace falta Docker para este ejercicio: los escáneres corren en GitHub, no en tu máquina.

> En cada paso vas a ver un 📍 que te dice **dónde tenés que estar parado** en la terminal. Si en algún momento no sabés dónde estás, corré `pwd` (en Windows PowerShell también funciona).

## Paso 0 — Preparar git (una sola vez)

📍 **Cualquier carpeta.**

Fijate si git ya sabe quién sos:

```bash
git config --global user.name
git config --global user.email
```

Si alguno de los dos no muestra nada, configuralo con tus datos:

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-mail@ejemplo.com"
```

### Crear un token para poder pushear

GitHub no acepta tu contraseña desde la terminal: necesitás un **token**. Además, para subir archivos dentro de `.github/workflows/`, el token tiene que tener un permiso especial.

1. En GitHub: tu foto (arriba a la derecha) → **Settings** → **Developer settings** (abajo de todo a la izquierda) → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
2. *Note*: `devsecops-modulo-07`. *Expiration*: 7 días alcanza.
3. Marcá los scopes **`repo`** y **`workflow`**. ⚠️ Sin `workflow`, el push del Paso 4 falla con `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope`.
4. **Generate token** y **copialo ya**: GitHub no te lo vuelve a mostrar.

Cuando `git push` te pida *Username*, ponés tu usuario de GitHub; cuando te pida *Password*, **pegás el token**. En Mac queda guardado en el llavero y no te lo vuelve a pedir.

> Si ya usás GitHub desde la terminal con SSH o con GitHub CLI (`gh auth login`), podés saltear el token y usar lo que ya tenés.

## Paso 1 — Conocer el archivo que vas a automatizar

📍 **Parate en la carpeta de la práctica**, la que tiene adentro `app/`, `terraform/` y `README.md`:

```bash
cd ruta/a/practica-modulo-07
ls -a
```

Tenés que ver, entre otras cosas, una carpeta **`.github`** (empieza con punto, por eso hace falta `ls -a` para verla). Adentro está el pipeline:

```bash
ls .github/workflows/
```

```
devsecops.yml
```

Este archivo es **todo** lo que necesita GitHub Actions: cualquier `.yml` que esté en `.github/workflows/` de un repositorio, GitHub lo ejecuta automáticamente. No hay que instalar ni activar nada.

Ahora vas a recorrerlo con cuatro preguntas. Podés abrirlo en tu editor (`code .github/workflows/devsecops.yml` si usás VS Code) o usar estos comandos:

**1. ¿Cuándo se ejecuta?**

```bash
sed -n '/^on:/,/^$/p' .github/workflows/devsecops.yml
```

```
on:
  push:
    branches: [ main ]
  pull_request:
```

Se ejecuta en cada `push` a `main` **y** en cada pull request.

**2. ¿Qué jobs tiene?**

```bash
grep -E "^  [a-z]+:$" .github/workflows/devsecops.yml
```

```
  push:
  sast:
  dependencias:
  imagen:
  infraestructura:
  dast:
```

(El primero, `push:`, es parte del bloque `on:`; los otros cinco son los jobs.) Cada uno es un escaneo que ya hiciste a mano:

| Job | Herramienta | Lo hiciste en |
|---|---|---|
| `sast` | Semgrep | Ejercicio 1 |
| `dependencias` | Trivy (`fs`) + Gitleaks | Ejercicio 2 |
| `imagen` | Trivy (`image`) | Ejercicio 3 |
| `dast` | OWASP ZAP | Ejercicio 4 |
| `infraestructura` | Checkov | Bonus de este ejercicio |

**3. ¿En qué orden corren?**

```bash
grep -n "needs:" .github/workflows/devsecops.yml
```

```
104:    needs: [ imagen ]
```

Solo `dast` tiene `needs`: espera a que termine `imagen`, porque no tiene sentido atacar una app que ni siquiera se pudo construir. **Los otros cuatro arrancan todos juntos, en paralelo.**

**4. ¿Bloquea o solo avisa?**

```bash
grep -nE "continue-on-error|exit-code|soft_fail" .github/workflows/devsecops.yml
```

```
42:        continue-on-error: true
59:          exit-code: '0'    # ponelo en '1' cuando quieras bloquear
65:        continue-on-error: true
82:          exit-code: '0'
96:          soft_fail: true   # ponelo en false cuando quieras bloquear
123:        continue-on-error: true
```

Las tres opciones dicen lo mismo con distintas palabras: **"si encontrás algo, mostralo, pero no hagas fallar el pipeline"**. Está puesto a propósito: al introducir escáneres en un proyecto que ya existe, primero mirás, después bloqueás. Si bloqueás desde el día uno, el equipo no puede trabajar y alguien desactiva el pipeline en una semana. En el Paso 6 lo vas a cambiar para que bloquee.

✅ **Salió bien si** podés contestar sin mirar: cuándo corre, cuántos jobs tiene, cuál espera a cuál y por qué no bloquea.

## Paso 2 — Crear el repositorio en GitHub

📍 **En el navegador**, no en la terminal.

El workflow busca las carpetas `app/` y `terraform/` **en la raíz del repositorio**. Por eso se usa un repositorio nuevo solo para esta práctica: si lo metés en una subcarpeta de otro repo, las rutas no coinciden y los jobs fallan.

1. Entrá a <https://github.com/new>.
2. *Repository name*: `devsecops-modulo-07`.
3. Visibilidad: **Public**. En repos públicos GitHub Actions es gratis y Gitleaks no pide licencia.
4. **No** marques *Add a README file*, ni *.gitignore*, ni *license*: el repo tiene que quedar **vacío**.
5. **Create repository**.

✅ **Salió bien si** ves una página que dice *"Quick setup"* con una URL del tipo `https://github.com/<tu-usuario>/devsecops-modulo-07.git`. Copiala: la usás en el paso siguiente.

## Paso 3 — Subir la práctica a `main`, *sin* el pipeline

Primero subís el código **sin** el workflow. Después el pipeline entra con un pull request, que es como se hace en un equipo real: nadie mete cambios de CI directo en `main`.

📍 **Parate en la carpeta que contiene a `practica-modulo-07`** (un nivel arriba). Comprobalo:

```bash
ls
```

Tenés que ver `practica-modulo-07` en la lista.

Hacé una copia en tu carpeta personal, para no mezclar el repositorio con el material original, y entrá a la copia:

```bash
cp -R practica-modulo-07 ~/devsecops-modulo-07
cd ~/devsecops-modulo-07
```

> **Windows PowerShell:** `Copy-Item -Recurse practica-modulo-07 ~\devsecops-modulo-07`

📍 **Desde acá en adelante, todo se corre dentro de `~/devsecops-modulo-07`.** Comprobalo:

```bash
pwd
ls
```

`pwd` tiene que terminar en `/devsecops-modulo-07` y `ls` tiene que mostrar `app`, `finops`, `terraform` y `README.md`.

Ahora convertí la carpeta en un repositorio y subila (reemplazá `<tu-usuario>`):

```bash
git init -b main
git add . ':!.github'
git status
```

`git add . ':!.github'` agrega todo **menos** la carpeta `.github`. En la salida de `git status` tenés que ver los archivos de `app/`, `terraform/`, etc. en verde, y **no** tiene que aparecer `.github`.

```bash
git commit -m "practica modulo 7"
git remote add origin https://github.com/<tu-usuario>/devsecops-modulo-07.git
git push -u origin main
```

Si te pide usuario y contraseña, usá tu usuario y el **token** del Paso 0.

> **Si el push falla con `GH013: Repository rule violations` / `Push cannot contain secrets`:** te frenó el *push protection* de GitHub, que detectó la API key de Stripe de `app_insegura.py`. Es exactamente lo que hace Gitleaks, pero del lado del servidor. Como es una clave falsa de laboratorio, abrí el link que aparece en el mensaje, elegí **"It's used in tests"**, **Allow secret**, y repetí el `git push -u origin main`. En un proyecto real, ese mensaje significa: **no subas eso y rotá la clave.**

✅ **Salió bien si** al recargar la página del repo en GitHub ves las carpetas `app`, `finops`, `terraform` y el `README.md`. **No** tiene que aparecer `.github`, y la pestaña **Actions** no tiene que mostrar ninguna ejecución todavía.

## Paso 4 — Agregar el pipeline en una rama

📍 **Seguís en `~/devsecops-modulo-07`.**

Creá una rama, agregá **solo** el workflow y subila:

```bash
git checkout -b sec/devsecops
git add .github/workflows/devsecops.yml
git status
```

`git status` tiene que decir `On branch sec/devsecops` y mostrar un solo archivo nuevo: `.github/workflows/devsecops.yml`.

```bash
git commit -m "ci: agrego pipeline de seguridad"
git push -u origin sec/devsecops
```

En la salida del push vas a ver algo así:

```
remote: Create a pull request for 'sec/devsecops' on GitHub by visiting:
remote:      https://github.com/<tu-usuario>/devsecops-modulo-07/pull/new/sec/devsecops
```

✅ **Salió bien si** el push terminó sin errores y ves ese link.

## Paso 5 — Abrir el pull request y ver el pipeline

📍 **En el navegador.**

1. Abrí el link del paso anterior. (Si lo perdiste: entrá al repo y vas a ver un cartel amarillo con el botón **Compare & pull request**.)
2. Revisá que arriba diga `base: main` ← `compare: sec/devsecops`.
3. **Create pull request**.

### Qué tenés que ver en el pull request

Bajá hasta el cuadro de **checks**, arriba del botón de merge. Al principio dice *"Some checks haven't completed yet"*, con cinco líneas:

```
DevSecOps / SAST — análisis del código (pull_request)
DevSecOps / SCA — dependencias y secretos (pull_request)
DevSecOps / Escaneo de la imagen Docker (pull_request)
DevSecOps / IaC — Terraform y manifiestos (pull_request)
DevSecOps / DAST — OWASP ZAP contra la app viva (pull_request)
```

Cada una tiene un círculo amarillo (corriendo), un tilde verde (terminó) o una cruz roja (falló). DAST arranca último, cuando termina *Escaneo de la imagen Docker*. Todo tarda entre 3 y 6 minutos.

Al terminar, el cuadro tiene que decir **"All checks have passed"** con los cinco en verde.

### Qué tenés que ver en la pestaña Actions

1. Arriba del repo, pestaña **Actions**.
2. Hacé clic en la ejecución **"ci: agrego pipeline de seguridad"**.
3. Vas a ver el **grafo**: cuatro cajas una al lado de la otra y una flecha desde *Escaneo de la imagen Docker* hacia *DAST*. Es el `needs` que viste en el Paso 1.
4. Hacé clic en cada caja y abrí los pasos (las flechitas ▸) para ver la salida. **Es la misma salida que viste en tu terminal**, porque son las mismas herramientas:

| Job | Paso que tenés que abrir | Qué tenés que encontrar |
|---|---|---|
| SAST | *Semgrep* | Los hallazgos en `app_insegura.py`: `shell=True`, `debug=True`, la API key |
| SCA | *Trivy — vulnerabilidades en dependencias* | La tabla con las vulnerabilidades de `requirements.txt` |
| SCA | *gitleaks — secretos en el historial de Git* | `leaks found` con la clave de Stripe |
| Imagen | *Trivy — vulnerabilidades del sistema base* | La tabla HIGH/CRITICAL de Debian y Python |
| IaC | *Checkov — revisión de Terraform* | Los `FAILED` sobre `terraform/main.tf` |
| DAST | *OWASP ZAP baseline scan* | Los `WARN-NEW` del ejercicio 4 |

5. Volvé al resumen de la ejecución y bajá hasta **Artifacts**: ahí está `zap_scan`, el reporte completo de ZAP en HTML, para descargar.

> **¿Por qué todo está en verde si hay hallazgos?** Por lo que viste en el Paso 1, pregunta 4. En los jobs SAST y SCA vas a ver que el paso de Semgrep o de Gitleaks tiene una cruz roja o un ícono naranja, pero el job igual termina en verde: es el `continue-on-error`. En Trivy y Checkov ni siquiera se marca, por `exit-code: '0'` y `soft_fail: true`. Es el modo "observar".

✅ **Salió bien si:**
- El pull request dice **All checks have passed** con los cinco checks.
- En *Actions* ves el grafo con DAST conectado a la imagen.
- Encontraste en los logs al menos un hallazgo de cada herramienta.
- Descargaste el artifact de ZAP.

📸 **Captura para la entrega** (`06-pipeline.png`): el cuadro de checks del pull request, o el grafo de *Actions*.

## Paso 6 — Hacer que bloquee (opcional)

Ahora vas a pasar el escaneo de imagen de "observar" a "bloquear".

📍 **Seguís en `~/devsecops-modulo-07`, en la rama `sec/devsecops`.** Comprobalo con `git branch`: tiene que tener un `*` al lado de `sec/devsecops`.

Abrí `.github/workflows/devsecops.yml` en tu editor y buscá el job `imagen` (alrededor de la línea 78). Cambiá:

```yaml
          exit-code: '0'
```

por:

```yaml
          exit-code: '1'
```

⚠️ Hay dos `exit-code: '0'` en el archivo. El que hay que cambiar es el del job **`imagen`**, el que está debajo de `image-ref: practica:ci`.

```bash
git commit -am "ci: el escaneo de imagen bloquea"
git push
```

📍 **En el navegador**, volvé al pull request. Se actualiza solo y arranca una ejecución nueva.

✅ **Salió bien si** *Escaneo de la imagen Docker* queda con **cruz roja**, el cuadro dice **"Some checks were not successful"** y DAST aparece como *skipped*: como depende de la imagen, ni se ejecuta.

> En un equipo real, además, en *Settings → Branches → Add branch ruleset* se exige que este check pase para poder mergear a `main`. Así, GitHub directamente no te deja apretar el botón de merge.

### Arreglarlo para que vuelva a verde

Aplicá lo que aprendiste en los ejercicios 2 y 3. 📍 **Seguís en `~/devsecops-modulo-07`.**

1. **`app/requirements.txt`**: reemplazá las versiones viejas por las actualizadas del ejercicio 2, Paso 3:
   ```
   flask==3.1.3
   requests==2.32.5
   jinja2==3.1.6
   pyyaml==6.0.2
   ```
2. **`app/Dockerfile`**: cambiá `FROM python:3.9-slim` por `FROM python:3.12-slim` y, en la línea de abajo, agregá:
   ```dockerfile
   RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
   ```
3. **`.github/workflows/devsecops.yml`**: en el mismo paso de Trivy del job `imagen`, agregá `ignore-unfixed: true` debajo del `exit-code: '1'`. Respetá la indentación:
   ```yaml
             exit-code: '1'
             ignore-unfixed: true
   ```
   Así solo bloquea lo que tiene arreglo disponible (ejercicio 3, Paso 4).

```bash
git status
```

Tienen que aparecer los tres archivos como modificados.

```bash
git commit -am "fix: imagen base nueva y dependencias actualizadas"
git push
```

✅ **Salió bien si** en el pull request los cinco checks vuelven a verde. **Esa es la secuencia real: el pipeline te frena, arreglás y vuelve a pasar.**

Si querés cerrar el circuito, tocá **Merge pull request**. En *Actions* vas a ver una ejecución más, esta vez disparada por el `push` a `main`: es la otra mitad del `on:` que leíste en el Paso 1.

## Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Support for password authentication was removed` | Pusiste tu contraseña en vez del token | Usá el token del Paso 0 |
| `refusing to allow a Personal Access Token to create or update workflow` | Al token le falta el scope `workflow` | Generá uno nuevo con `repo` + `workflow` |
| `GH013: Push cannot contain secrets` | *Push protection* detectó la API key de prueba | Ver la nota del Paso 3 |
| `error: src refspec main does not match any` | No se hizo el commit (el `git add` no agregó nada) | Revisá que estés en `~/devsecops-modulo-07` y repetí `git add` y `git commit` |
| `remote origin already exists` | Ya corriste `git remote add` antes | `git remote set-url origin https://github.com/<tu-usuario>/devsecops-modulo-07.git` |
| La pestaña *Actions* está vacía después del Paso 4 | El archivo no quedó en `.github/workflows/` en la raíz, o Actions está desactivado | Revisá que en GitHub, dentro de la rama `sec/devsecops`, exista `.github/workflows/devsecops.yml`. Si existe, revisá *Settings → Actions → General* |
| `docker build` falla con `app/: no such file or directory` | La práctica quedó dentro de una subcarpeta | `app/` tiene que estar en la raíz del repo |
| El job de imagen falla en `pip install` | `requirements.txt` tiene versiones que no instalan en esa versión de Python | Ver ejercicio 3 |
| Gitleaks pide `GITLEAKS_LICENSE` | El repo es de una **organización** | Gitleaks es gratis solo en cuentas personales: usá un repo personal |

## ✅ Cómo saber que salió bien (todo el ejercicio)

- El pull request muestra los cinco checks del pipeline en verde
- Encontraste en los logs los mismos hallazgos que en los ejercicios 1 a 4
- Podés explicar por qué el pipeline está en verde aunque haya hallazgos
- *(Opcional)* Lo hiciste bloquear, viste la cruz roja y lo volviste a poner en verde

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
    ├── 05-finops.png
    └── 06-pipeline.png   ← opcional (bonus): los checks del pull request
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
