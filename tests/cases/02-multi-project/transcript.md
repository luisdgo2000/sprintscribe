# Planning conjunto · 2026-10-07

[00:00] Brian: Hoy vemos dos frentes: el Data Lake de Ventas y Facturación Electrónica.
[00:20] Brian: En el lake de ventas, Jorge, necesito la ingesta diaria de las ventas de los puntos de venta hacia la capa bronce. Finanzas quiere dejar de armar el reporte a mano.
[00:55] Jorge: Ok, uso el mismo conector que ya tenemos para inventario.
[01:10] Brian: Sofía, tú diseñas el modelo de la capa plata para ventas, con tienda, producto y fecha.
[01:30] Sofía: Lo hago y lo reviso con Jorge para que calce con la ingesta.
[02:00] Brian: Ahora facturación. El certificado de firma vence el 30. Carlos, renuévalo e instálalo en producción.
[02:25] Carlos: Necesito que infraestructura me dé acceso al almacén de certificados.
[02:40] Brian: Ana, el SAT publicó la versión 4.4 del XML. Ajusta el generador para que cumpla.
[03:00] Ana: Va, reviso el anexo técnico primero.
[03:20] Carlos: Ojo, en el portal del SAT aparece que el certificado vence el 15, no el 30.
[03:35] Brian: Hay que confirmarlo, pero igual lo renovamos ya.
