# Segundo Cerebro Kit

Continuidad entre personas y agentes con archivos Markdown locales.

El kit conserva decisiones, hechos verificados, pendientes y fuentes fuera del
chat. Permite preparar contexto de arranque con un límite de caracteres y revisar
enlaces rotos o ambiguos de una wiki. Usa Python 3.10+, sin dependencias externas.

## Probarlo

```sh
python brainkit.py --root examples index --pending
python brainkit.py --root examples context --topic documentacion --max-chars 4000
python brainkit.py --root examples check
python -m unittest -v
```

## Usarlo en un proyecto

Creá una carpeta vacía. Después generá un relevo:

```sh
mkdir mi-cerebro
python brainkit.py --root mi-cerebro note "Revisar documentación" --author pedro --topic documentacion
```

Completá las secciones del archivo en `notes/`. Los encabezados del formato son
`Date`, `Author`, `Topic`, `State`, `Resolution`, `Decisions`, `Verified`,
`Next steps`, `Limits` y `Sources`; el contenido puede escribirse en español.

Los estados admitidos son `pending`, `in_progress`, `incorporated` y `discarded`.
Los dos últimos requieren una resolución con destino o motivo. Un estado escrito
dentro del cuerpo no puede cerrar una nota.

La búsqueda ignora mayúsculas y acentos. El contexto avisa cuántos pendientes
coinciden y cuántos entraron. Que una nota no entre en el presupuesto no significa
que esté resuelta. La revisión devuelve código 1 si encuentra problemas y sirve
para automatizar chequeos.

Esta primera versión pública está inspirada en el uso real de un segundo cerebro
privado. Se comparte la herramienta y un ejemplo sintético, sin datos del negocio,
correos, compradores, cursos ni credenciales. Todavía no se acredita adopción externa.

## Compartir herramientas sin compartir la memoria

`release` recibe una lista explícita de archivos, revisa indicadores comunes de
secretos y genera un ZIP con hashes SHA-256. No incluye archivos fuera de la lista
ni historial de Git. Rechaza symlinks, rutas que escapan de la raíz y destinos que
ya existen. El escáner es heurístico: la revisión humana sigue siendo necesaria.

```sh
python brainkit.py --root . release --allowlist public-files.json --output ../segundo-cerebro-publico.zip
```

Consultá [el protocolo](PROTOCOL.md), [las limitaciones](README.md#boundaries) y
[cómo contribuir](CONTRIBUTING.md). Licencia MIT.
