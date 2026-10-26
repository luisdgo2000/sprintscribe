# Refinamiento Portal de Clientes · 2026-10-09

[00:00] Brian: Para este sprint del portal necesitamos que Ana desarrolle la recuperación de contraseña por correo, que Carlos migre el formulario de registro a la nueva librería de componentes, y que Ana también se encargue de la auditoría de inicios de sesión.
[00:35] Ana: Ok, las dos mías las hago en ese orden.
[03:10] María: Ayer soporte reportó clientes con dos cuentas. Se registraron una vez con mayúsculas en el correo y otra en minúsculas.
[03:40] Brian: Eso es grave, los pedidos quedan repartidos entre cuentas.
[12:05] Brian: Carlos, la migración del formulario de registro ya no la vamos a hacer. En su lugar necesitamos una tarea para resolver el problema de las cuentas duplicadas que acabamos de comentar.
[12:30] Carlos: Va. Normalizo el correo al registrarse y reviso cómo detectar las cuentas que ya están duplicadas.
[12:50] Brian: Perfecto, la migración la retomamos cuando haya espacio.
