# Hospeda

Aplicación local para registrar habitaciones y alquileres de un hospedaje. Está pensada para que el control diario sea sencillo y para conservar un respaldo de los datos del huésped y de cada alquiler.

## Funciones

- Registrar, editar y organizar habitaciones disponibles y ocupadas.
- Guardar alquileres con huésped, celular, DNI, fechas, modalidad de cobro, monto y estado de pago.
- Registrar gastos y consultar indicadores del mes en la aplicación.
- Guardar la información localmente en SQLite y actualizar `hospedaje.xlsx` con los datos básicos de los alquileres.
- Crear un respaldo JSON local.

## Tecnologías

- HTML, CSS y JavaScript para la interfaz.
- Python para el servidor local.
- SQLite para guardar los registros de la aplicación.
- Excel (`.xlsx`) para el respaldo de los alquileres.

## Cómo iniciar en Windows

1. Instala Python 3.9 o posterior.
2. Abre `iniciar_hospeda.bat`.
3. La aplicación se abrirá en el navegador. Para crear un acceso directo en el escritorio, abre `crear_acceso_directo.bat`.

La aplicación funciona en la misma computadora sin publicar los datos en un servicio externo. Los archivos de datos locales están excluidos de Git mediante `.gitignore`.

## Archivos principales

- `index.html`: interfaz y lógica de la aplicación.
- `server.py`: servidor local, persistencia SQLite y generación del Excel.
- `iniciar_hospeda.bat`: inicia el servidor y abre la aplicación.
- `crear_acceso_directo.bat`: crea un acceso directo de Windows.
- `hospeda-logo.svg` y `hospeda.ico`: identidad visual.

## Estado

Proyecto en desarrollo. Antes de usarlo con datos reales, verifica los cálculos y conserva una copia de seguridad independiente. No incluyas en el repositorio el Excel, la base de datos SQLite ni los respaldos JSON, porque pueden contener nombres, DNI y teléfonos.
