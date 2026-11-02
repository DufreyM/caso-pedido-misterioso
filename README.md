# El caso del pedido misterioso

Juego de misterio con datos para la demostración de **Streamlit** (Tarea 4, Grupo 6, CC3084).

Cacao Quetzal, una cadena de chocolaterías con 9 tiendas, recibe una nota anónima: alguien hizo
un pedido "muy dulce" durante un mes entero y dejó una sorpresa para quien descubra **dónde,
cuándo y qué** pidió. Los equipos usan el dashboard (filtros, indicadores y gráficas) para
encontrarlo y acusan; la app solo les dice cuántos de los 3 datos aciertan.

## Ejecutar

```bash
cd Streamlit          # importante: el tema (.streamlit/config.toml) se lee desde aquí
pip install -r requirements.txt
streamlit run app.py
```

- Juego: `http://localhost:8501`
- Tablero en vivo para proyectar: `http://localhost:8501/?modo=presentador`
  (el PIN está en `PIN_PRESENTADOR` y desbloquea "mostrar solución" y "vaciar tablero").

## Que la clase juegue desde sus celulares

El tablero se comparte entre todos los que se conecten **al mismo servidor**.

- **Streamlit Community Cloud (recomendado):** suban esta carpeta a un repo de GitHub, entren a
  share.streamlit.io → *Create app* → elijan el repo y `app.py`. Compartan el link (o un QR).
- **Misma red Wi-Fi:** `streamlit run app.py` y compartan la *Network URL* que imprime la terminal.
  La red de la universidad puede bloquear conexiones entre dispositivos; prueben antes.

## Personalizar (arriba de `app.py`)

| Variable | Para qué |
|---|---|
| `SORPRESA` | El mensaje que ven al resolver. Pongan aquí su sorpresa real. |
| `SOLUCION` | Tienda, mes y producto del pedido. Los datos se generan a partir de aquí. |
| `PUNTOS_INICIALES`, `COSTO_PISTA`, `COSTO_ERROR` | Reglas de puntaje. |

## Solución (no la proyecten)

**Mazatenango · Agosto · Bombones.** En el total anual Mazatenango casi empata con Escuintla;
el pedido solo aparece al filtrar la región Sur y mirar la pestaña *Tiempo*, y luego dejar solo
agosto en *Productos* (bombones +224 % contra su mes típico, ticket promedio +77 %).

Pistas falsas a propósito: febrero y mayo (temporada en todas las tiendas), Cobán cerrado dos semanas
en mayo y Zona 10 como la tienda que más vende.

## Diseño de la interacción (HCI)

- **Visibilidad del estado:** tiempo en vivo, puntos, acusaciones, pistas y el resumen "Viendo: …"
  de los filtros activos.
- **Meta siempre visible:** la tarjeta "Su misión" (arriba) muestra las 3 preguntas, la pista de la nota
  para cada una y qué filtro usar; ahí mismo anotan su sospecha y acusan.
- **Prevención de errores:** la acusación se hace con listas (no texto libre); el botón "Acusar" se activa
  solo con las 3 sospechas; combinaciones repetidas no restan puntos y reiniciar pide confirmación.
- **Reconocer antes que recordar:** la nota siempre a la mano, historial de acusaciones, tiendas
  con su región en la lista.
- **Retroalimentación que guía:** tras cada acusación, cada tarjeta marca "Correcto" o "No es este";
  pistas opcionales con costo visible. Pensado para resolverse en unos 5 minutos.
- **Consistencia:** todas las vistas responden a los mismos filtros; cada región, tienda y
  producto conserva su color en todas las gráficas (paleta segura para daltonismo) y nunca
  depende solo del color (leyendas y etiquetas).
- **Control y libertad:** "Limpiar filtros", reiniciar juego, retomar si recargan la página.
- **Para la exposición:** el interruptor "Ver el código detrás" muestra el código de cada parte
  y el contador de ejecuciones del script ilustra el modelo de re-ejecución de Streamlit.

## Paleta "Grupo 6"

Tomada de la presentación y ampliada; definida en `.streamlit/config.toml` y al inicio de `app.py`.

| Rol | Color |
|---|---|
| Tinta (texto, barra lateral) | `#0E1B4D` |
| Azul real (principal) | `#1F4FD8` |
| Azul cielo | `#3B82F6` |
| Hielo (fondos suaves) | `#EAF0FF` |
| Turquesa / turquesa claro | `#0E9384` / `#2DD4BF` |
| Coral | `#E04A4F` |
| Ámbar | `#D08300` |
| Fondo | `#F5F7FD` |

Las gráficas usan azul, coral, turquesa y ámbar en ese orden fijo; la combinación pasa las pruebas
de separación para daltonismo y contraste ≥ 3:1 sobre blanco.
