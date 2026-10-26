# Refinamiento Portal de Clientes · 2026-10-06

[00:00] Brian: Arrancamos con el Portal de Clientes. Lo que más piden en soporte es poder descargar las facturas en PDF desde el portal; hoy nos escriben por correo para pedirlas y eso son unas cuarenta solicitudes por semana.
[00:42] Brian: Ana, necesito que hagas el endpoint que devuelva la factura en PDF. Ya existe el servicio de facturas, solo hay que exponerlo con el mismo control de permisos que usa el historial.
[01:10] Ana: Va. El PDF lo genera hoy el servicio de facturación, así que lo consumo de ahí. Calculo un par de días.
[01:25] Brian: Carlos, tú agregas el botón de descarga en la pantalla de historial de facturas, cuando Ana tenga el endpoint.
[01:40] Carlos: Perfecto, depende del contrato del endpoint, Ana me lo pasas.
[02:05] Brian: María, cuando esté integrado lo pruebas en QA con clientes de prueba que tengan facturas de varios meses.
[02:20] María: Sí, preparo los casos con facturas viejas y nuevas.
[02:40] Brian: Con eso cerramos el tema de facturas para este sprint.
