import asyncio
import json
import os
import time
import unicodedata

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from telegram import Bot


# ============================================================
# CONFIGURACIÓN
# ============================================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = int(os.getenv("TELEGRAM_USER_ID"))

ARCHIVO_ESTADO = "estado_productos.json"
ARCHIVO_VISTOS = "productos_nuevos_vistos.json"
ARCHIVO_ESTADO_NUEVOS = "estado_productos_nuevos.json"

INTERVALO_MINUTOS = 5


# ============================================================
# PRODUCTOS FIJOS
# ============================================================

PRODUCTOS_FIJOS = [
    "B0H783FY5Z",
    "B0H77VYKSM",
    "B0H77XNKKK",
    "B0H784PD4X",
    "B0H77W4411",
    "B0H7818YHY",
    "B0H7815T4Y",
    "B0H784PJ49",
    "B0H788QPS9",
    "B0H786LQ7Z",
    "B0H77XNCGM",
    "B0H78194FL",
    "B0H783JJ66",
    "B0H784MT1P",
    "B0H77W3H3C",
    "B0H78184DH",
    "B0H77XCW4M",
    "B0H786SFFS",
    "B0H77XJC85",
    "B0H78B8XQW",
]

PRODUCTOS_FIJOS_SET = set(PRODUCTOS_FIJOS)


# ============================================================
# BÚSQUEDAS
# ============================================================

BUSQUEDAS = [
    "Pokemon TCG 30TH Celebration",
    "Pokemon TCG",
    "Pokemon 30",
    "Pokemon Celebration",
]


# ============================================================
# ESTADO — PRODUCTOS FIJOS
# ============================================================

def cargar_estado():

    if not os.path.exists(ARCHIVO_ESTADO):
        return {}

    try:

        with open(
            ARCHIVO_ESTADO,
            "r",
            encoding="utf-8"
        ) as archivo:

            return json.load(archivo)

    except Exception:

        return {}


def guardar_estado(estado):

    with open(
        ARCHIVO_ESTADO,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            estado,
            archivo,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# ESTADO — PRODUCTOS NUEVOS
# ============================================================

def cargar_vistos():

    if not os.path.exists(ARCHIVO_VISTOS):
        return set()

    try:

        with open(
            ARCHIVO_VISTOS,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(archivo)

        return set(datos)

    except Exception:

        return set()


def guardar_vistos(vistos):

    with open(
        ARCHIVO_VISTOS,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            sorted(list(vistos)),
            archivo,
            ensure_ascii=False,
            indent=2
        )


def cargar_estado_nuevos():

    if not os.path.exists(ARCHIVO_ESTADO_NUEVOS):
        return {}

    try:

        with open(
            ARCHIVO_ESTADO_NUEVOS,
            "r",
            encoding="utf-8"
        ) as archivo:

            return json.load(archivo)

    except Exception:

        return {}


def guardar_estado_nuevos(estado):

    with open(
        ARCHIVO_ESTADO_NUEVOS,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            estado,
            archivo,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# TELEGRAM
# ============================================================

async def enviar_telegram(mensaje):

    bot = Bot(token=TOKEN)

    try:

        await bot.send_message(
            chat_id=USER_ID,
            text=mensaje
        )

        return True

    finally:

        try:
            await bot.close()
        except Exception:
            pass


async def enviar_telegram_seguro(mensaje):

    try:

        return await enviar_telegram(mensaje)

    except Exception as error:

        print(
            "❌ Error enviando Telegram: "
            f"{error}"
        )

        return False


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar(texto):

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


# ============================================================
# DETECTAR 30TH ANIVERSARIO
# ============================================================

def es_30th_aniversario(titulo):

    texto = normalizar(titulo)

    return (
        "pokemon tcg" in texto
        and "30th celebration" in texto
    )


# ============================================================
# FORMATEAR TÍTULO
# ============================================================

def titulo_formateado(titulo):

    if es_30th_aniversario(titulo):

        if not titulo.startswith("⭐⭐⭐⭐⭐"):

            return "⭐⭐⭐⭐⭐ " + titulo

    return titulo


# ============================================================
# REGLAS DE BÚSQUEDA
# ============================================================

def cumple_reglas_busqueda(titulo):

    texto = normalizar(titulo)

    regla_1 = (
        "pokemon tcg 30th celebration"
        in texto
    )

    regla_2 = (
        "pokemon" in texto
        and "tcg" in texto
    )

    regla_3 = (
        "pokemon" in texto
        and "30" in texto
    )

    regla_4 = (
        "pokemon" in texto
        and "celebration" in texto
    )

    return (
        regla_1
        or regla_2
        or regla_3
        or regla_4
    )


# ============================================================
# REVISAR PRODUCTO AMAZON
# ============================================================

async def revisar_producto(asin, browser):

    url = f"https://www.amazon.com.mx/dp/{asin}"

    page = await browser.new_page(
        locale="es-MX",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
    )

    try:

        print(
            f"\n🔎 Revisando {asin}..."
        )

        respuesta = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        if respuesta is None:

            print(
                "⚠️ Amazon no respondió correctamente."
            )

            return None

        if respuesta.status >= 400:

            print(
                f"⚠️ Amazon respondió con HTTP "
                f"{respuesta.status}"
            )

            return None

        # ----------------------------------------------------
        # TÍTULO
        # ----------------------------------------------------

        titulo = await page.title()

        # ----------------------------------------------------
        # PRECIO
        # ----------------------------------------------------

        precio_elemento = page.locator(
            ".a-price .a-offscreen"
        ).first

        if await precio_elemento.count() > 0:

            try:

                precio = (
                    await precio_elemento
                    .inner_text()
                ).strip()

            except Exception:

                precio = "No disponible"

        else:

            precio = "No disponible"

        # ----------------------------------------------------
        # DISPONIBILIDAD
        # ----------------------------------------------------

        disponibilidad = page.locator(
            "#availability"
        ).first

        if await disponibilidad.count() > 0:

            try:

                texto_disponibilidad = (
                    await disponibilidad
                    .inner_text()
                ).strip().lower()

            except Exception:

                texto_disponibilidad = ""

        else:

            texto_disponibilidad = ""

        # ----------------------------------------------------
        # BUYBOX
        # ----------------------------------------------------

        buybox = page.locator(
            "#buybox"
        ).first

        if await buybox.count() > 0:

            try:

                texto_compra = (
                    await buybox
                    .inner_text()
                ).strip().lower()

            except Exception:

                texto_compra = ""

        else:

            texto_compra = ""

        texto_completo = (
            texto_disponibilidad
            + "\n"
            + texto_compra
        ).lower()

        # ----------------------------------------------------
        # FRASES NO DISPONIBLE
        # ----------------------------------------------------

        frases_no_disponible = [

            "no disponible",

            "agotado",

            "temporalmente agotado",

            "actualmente no disponible",

            "out of stock",

            "ver opciones de compra",
        ]

        # ----------------------------------------------------
        # BOTÓN AGREGAR AL CARRITO
        # ----------------------------------------------------

        boton_carrito = page.locator(
            "#add-to-cart-button"
        ).first

        hay_boton_carrito = False

        if await boton_carrito.count() > 0:

            try:

                hay_boton_carrito = (
                    await boton_carrito.is_visible()
                    and await boton_carrito.is_enabled()
                )

            except Exception:

                hay_boton_carrito = False

        # ----------------------------------------------------
        # DETERMINAR DISPONIBILIDAD
        # ----------------------------------------------------

        if any(
            frase in texto_completo
            for frase in frases_no_disponible
        ):

            disponible = False

        elif hay_boton_carrito:

            disponible = True

        else:

            disponible = False

        if disponible:

            print("🟢 DISPONIBLE")

        else:

            print("🔴 NO DISPONIBLE")

        return {

            "asin": asin,

            "titulo": titulo,

            "precio": precio,

            "disponible": disponible,

            "url": url,
        }

    except Exception as error:

        print(
            f"❌ Error revisando {asin}: "
            f"{error}"
        )

        return None

    finally:

        await page.close()


# ============================================================
# BUSCAR PRODUCTOS
# ============================================================

async def buscar_productos(busqueda, browser):
    """Devuelve una lista si la búsqueda fue válida; None si falló."""
    print(f"\n🔍 BUSCANDO: {busqueda}")
    url = "https://www.amazon.com.mx/s?k=" + busqueda.replace(" ", "+")

    for intento in range(1, 3):
        page = await browser.new_page(
            locale="es-MX",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        try:
            respuesta = await page.goto(
                url, wait_until="domcontentloaded", timeout=30000
            )
            if respuesta is None:
                raise RuntimeError("Amazon no devolvió respuesta HTTP")

            if respuesta.status in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {respuesta.status}")
            if respuesta.status >= 400:
                raise RuntimeError(f"HTTP {respuesta.status}")

            contenido = (await page.locator("body").inner_text()).lower()
            marcas_bloqueo = (
                "robot check", "captcha", "enter the characters",
                "sorry, we just need to make sure", "no eres un robot",
                "verifica que eres una persona", "validatecaptcha",
            )
            if any(marca in contenido for marca in marcas_bloqueo):
                raise RuntimeError("Amazon mostró una página de verificación/bloqueo")

            tarjetas = page.locator('div[data-component-type="s-search-result"]')
            cantidad = await tarjetas.count()
            print(f"📦 Resultados encontrados: {cantidad}")

            if cantidad == 0:
                frases_sin_resultados = (
                    "no hay resultados", "no results for", 
                    "no se han encontrado resultados", "no encontramos resultados",
                )
                if not any(frase in contenido for frase in frases_sin_resultados):
                    raise RuntimeError(
                        "La página no contiene tarjetas ni un mensaje claro de búsqueda vacía"
                    )
                return []

            resultados = []
            for indice in range(cantidad):
                tarjeta = tarjetas.nth(indice)
                try:
                    asin = await tarjeta.get_attribute("data-asin")
                    if not asin or asin in PRODUCTOS_FIJOS_SET:
                        continue
                    titulo_elemento = tarjeta.locator("h2").first
                    if await titulo_elemento.count() == 0:
                        continue
                    titulo = (await titulo_elemento.inner_text()).strip()
                    if not titulo or not cumple_reglas_busqueda(titulo):
                        continue
                    precio_elemento = tarjeta.locator(".a-price .a-offscreen").first
                    precio = "No disponible"
                    if await precio_elemento.count() > 0:
                        try:
                            precio = (await precio_elemento.inner_text()).strip()
                        except Exception:
                            pass
                    resultados.append({
                        "asin": asin,
                        "titulo": titulo,
                        "precio": precio,
                        "url": f"https://www.amazon.com.mx/dp/{asin}",
                    })
                except Exception as error:
                    print(f"⚠️ No se pudo leer una tarjeta: {error}")
            return resultados

        except Exception as error:
            print(f"⚠️ Búsqueda fallida (intento {intento}/2): {error}")
            if intento == 1:
                await asyncio.sleep(8)
            else:
                print(f"❌ No se pudo completar la búsqueda: {busqueda}")
                return None
        finally:
            await page.close()

    return None


# ============================================================
# EJECUTAR CICLO
# ============================================================

async def ejecutar_ciclo(
    browser,
    estado_fijos,
    vistos,
    estado_nuevos
):

    inicio = time.time()

    alertas_fijos = []

    alertas_nuevos = []

    productos_encontrados = {}

    nuevos_detectados = []

    # ========================================================
    # PRODUCTOS FIJOS
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "🎯 REVISANDO PRODUCTOS FIJOS"
    )

    print(
        "========================================"
    )

    for asin in PRODUCTOS_FIJOS:

        resultado = await revisar_producto(
            asin,
            browser
        )

        if resultado is None:

            print(
                f"⚠️ No se actualiza "
                f"el estado de {asin}"
            )

            continue

        disponible = resultado[
            "disponible"
        ]

        estado_previo = estado_fijos.get(
            asin
        )

        if (
            estado_previo is False
            and disponible is True
        ):

            print(
                "\n🚨 ¡PRODUCTO FIJO DISPONIBLE!"
            )

            alertas_fijos.append(
                resultado
            )

        elif (
            estado_previo is True
            and disponible is True
        ):

            print(
                "ℹ️ Sigue disponible. "
                "Sin alerta."
            )

        estado_fijos[asin] = disponible

    # ========================================================
    # BÚSQUEDAS
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "🔎 BUSCANDO PRODUCTOS NUEVOS"
    )

    print(
        "========================================"
    )

    busquedas_completas = True

    for busqueda in BUSQUEDAS:
        resultados = await buscar_productos(busqueda, browser)

        if resultados is None:
            busquedas_completas = False
            continue

        for producto in resultados:
            asin = producto["asin"]
            if asin in PRODUCTOS_FIJOS_SET:
                continue
            productos_encontrados[asin] = producto

    if not busquedas_completas:
        print(
            "⚠️ Una o más búsquedas fallaron. "
            "Se omite el procesamiento de productos nuevos/stock "
            "para no alterar memorias con resultados incompletos."
        )
        productos_encontrados = {}

    print(
        "\n📦 Productos únicos encontrados: "
        f"{len(productos_encontrados)}"
    )

    # ========================================================
    # PROCESAR PRODUCTOS ENCONTRADOS
    # ========================================================

    for asin, producto in productos_encontrados.items():

        titulo = producto["titulo"]

        titulo_mostrado = titulo_formateado(
            titulo
        )

        producto["titulo"] = titulo_mostrado

        print(
            "\n----------------------------------------"
        )

        print(
            f"📦 {titulo_mostrado}"
        )

        print(
            f"🆔 ASIN: {asin}"
        )

        es_nuevo = asin not in vistos

        if es_nuevo:

            print(
                "🆕 PRODUCTO NUEVO"
            )

            nuevos_detectados.append(
                producto
            )

        # ----------------------------------------------------
        # COMPROBAR STOCK
        # ----------------------------------------------------

        print(
            "🔎 Comprobando disponibilidad..."
        )

        resultado_stock = await revisar_producto(
            asin,
            browser
        )

        if resultado_stock is None:

            print(
                "⚠️ No se pudo comprobar "
                "la disponibilidad."
            )

            continue

        disponible = resultado_stock[
            "disponible"
        ]

        producto["precio"] = (
            resultado_stock["precio"]
        )

        producto["disponible"] = disponible

        estado_previo = estado_nuevos.get(
            asin
        )

        # ----------------------------------------------------
        # PRODUCTO NUEVO
        # ----------------------------------------------------

        if es_nuevo:

            print(
                "🆕 Guardando como "
                "producto nuevo."
            )

            vistos.add(asin)

            mensaje = (
                "🆕 ¡PRODUCTO NUEVO!\n\n"
                f"📦 {titulo_mostrado}\n\n"
                f"💰 Precio: "
                f"{producto['precio']}\n\n"
                f"📊 Estado: "
                f"{'🟢 DISPONIBLE' if disponible else '🔴 NO DISPONIBLE'}\n\n"
                f"🔗 {producto['url']}"
            )

            alertas_nuevos.append(
                {
                    "mensaje": mensaje,
                    "tipo": "nuevo",
                    "producto": producto,
                }
            )

        # ----------------------------------------------------
        # PRODUCTO YA CONOCIDO
        # ----------------------------------------------------

        else:

            if (
                estado_previo is False
                and disponible is True
            ):

                print(
                    "🚨 ¡PRODUCTO VUELVE "
                    "A ESTAR DISPONIBLE!"
                )

                mensaje = (
                    "🚨 ¡PRODUCTO DISPONIBLE "
                    "NUEVAMENTE!\n\n"
                    f"📦 {titulo_mostrado}\n\n"
                    f"💰 Precio: "
                    f"{producto['precio']}\n\n"
                    f"🔗 {producto['url']}"
                )

                alertas_nuevos.append(
                    {
                        "mensaje": mensaje,
                        "tipo": "stock",
                        "producto": producto,
                    }
                )

            elif (
                estado_previo is True
                and disponible is True
            ):

                print(
                    "ℹ️ Sigue disponible. "
                    "Sin alerta."
                )

            elif (
                estado_previo is True
                and disponible is False
            ):

                print(
                    "ℹ️ Dejó de estar disponible. "
                    "Sin alerta."
                )

            elif (
                estado_previo is False
                and disponible is False
            ):

                print(
                    "ℹ️ Sigue no disponible. "
                    "Sin alerta."
                )

        estado_nuevos[asin] = disponible

    # ========================================================
    # GUARDAR MEMORIAS
    # ========================================================

    guardar_estado(
        estado_fijos
    )

    guardar_vistos(
        vistos
    )

    guardar_estado_nuevos(
        estado_nuevos
    )

    print(
        "\n💾 Memorias guardadas."
    )

    # ========================================================
    # TELEGRAM — FIJOS
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "📨 TELEGRAM — PRODUCTOS FIJOS"
    )

    print(
        "========================================"
    )

    for producto in alertas_fijos:

        mensaje = (
            "🚨 ¡PRODUCTO DISPONIBLE!\n\n"
            f"📦 {producto['titulo']}\n\n"
            f"💰 Precio: "
            f"{producto['precio']}\n\n"
            f"🔗 {producto['url']}"
        )

        enviado = await enviar_telegram_seguro(
            mensaje
        )

        if enviado:

            print(
                "📨 Aviso enviado a Telegram."
            )

    # ========================================================
    # TELEGRAM — NUEVOS / STOCK
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "📨 TELEGRAM — PRODUCTOS NUEVOS / STOCK"
    )

    print(
        "========================================"
    )

    for alerta in alertas_nuevos:

        enviado = await enviar_telegram_seguro(
            alerta["mensaje"]
        )

        if enviado:

            print(
                "📨 Aviso enviado a Telegram."
            )

    # ========================================================
    # RESUMEN
    # ========================================================

    duracion = time.time() - inicio

    print(
        "\n========================================"
    )

    print(
        "📊 RESUMEN DEL CICLO"
    )

    print(
        "========================================"
    )

    print(
        "🎯 Productos fijos revisados: "
        f"{len(PRODUCTOS_FIJOS)}"
    )

    print(
        "🚨 Alertas de productos fijos: "
        f"{len(alertas_fijos)}"
    )

    print(
        "📦 Productos encontrados: "
        f"{len(productos_encontrados)}"
    )

    print(
        "🆕 Productos nuevos: "
        f"{len(nuevos_detectados)}"
    )

    print(
        "📨 Alertas nuevos/stock: "
        f"{len(alertas_nuevos)}"
    )

    print(
        "🧠 Total histórico: "
        f"{len(vistos)}"
    )

    print(
        "⏱️ Duración del ciclo: "
        f"{duracion:.1f} segundos"
    )

    return duracion


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

async def main():

    estado_fijos = cargar_estado()

    vistos = cargar_vistos()

    estado_nuevos = cargar_estado_nuevos()

    print(
        "\n🤖 MONITOR AMAZON INICIADO"
    )

    print(
        f"⏱️ Revisando cada "
        f"{INTERVALO_MINUTOS} minutos."
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        try:

            print(
                "\\n"
                "===================================="
            )

            print(
                "🔄 NUEVA REVISIÓN"
            )

            print(
                "===================================="
            )

            await ejecutar_ciclo(
                browser,
                estado_fijos,
                vistos,
                estado_nuevos
            )

            print(
                "\\n✅ Ciclo terminado. "
                "Cerrando el monitor para esta ejecución."
            )

        finally:

            await browser.close()


# ============================================================
# ARRANCAR
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
