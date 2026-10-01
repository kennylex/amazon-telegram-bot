
# ============================================================
# BUSCAR PRODUCTOS
# ============================================================

async def buscar_productos(
    busqueda,
    browser
):

    print(
        f"\n🔍 BUSCANDO: {busqueda}"
    )

    page = await browser.new_page(
        locale="es-MX",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
    )

    resultados = []

    try:

        url = (
            "https://www.amazon.com.mx/s"
            f"?k={busqueda.replace(' ', '+')}"
        )

        respuesta = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        if respuesta is None:

            print(
                "⚠️ Amazon no respondió."
            )

            return resultados

        if respuesta.status >= 400:

            print(
                f"⚠️ Amazon respondió con HTTP "
                f"{respuesta.status}"
            )

            return resultados

        tarjetas = page.locator(
            'div[data-component-type="s-search-result"]'
        )

        cantidad = await tarjetas.count()

        print(
            f"📦 Resultados encontrados: {cantidad}"
        )

        for indice in range(cantidad):

            tarjeta = tarjetas.nth(indice)

            try:

                asin = await tarjeta.get_attribute(
                    "data-asin"
                )

                if not asin:
                    continue

                if asin in PRODUCTOS_FIJOS_SET:
                    continue

                titulo_elemento = tarjeta.locator(
                    "h2"
                ).first

                if await titulo_elemento.count() == 0:
                    continue

                titulo = (
                    await titulo_elemento
                    .inner_text()
                ).strip()

                if not titulo:
                    continue

                if not cumple_reglas_busqueda(
                    titulo
                ):
                    continue

                precio_elemento = tarjeta.locator(
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

                resultados.append({

                    "asin": asin,

                    "titulo": titulo,

                    "precio": precio,

                    "url": (
                        "https://www.amazon.com.mx"
                        f"/dp/{asin}"
                    ),
                })

            except Exception:

                continue

        return resultados

    except Exception as error:

        print(
            f"❌ Error en búsqueda "
            f"'{busqueda}': {error}"
        )

        return resultados

    finally:

        await page.close()
