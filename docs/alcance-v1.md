# Alcance v1

Sistema interno de gestión de reservas para departamentos de alquiler temporario. Lo usan solo los dueños; los huéspedes no tienen acceso.

## Contexto

Hoy las reservas se toman por WhatsApp o por teléfono y se anotan en una libreta. Los huéspedes pagan el total al llegar: no hay seña. El precio por noche varía según el mes y lo decide el dueño en cada caso.

## Funcionalidades y criterios de aceptación

### Cargar un departamento

- Nombre, dirección y máximo de huéspedes son obligatorios. Si falta alguno, el departamento no se da de alta.
- El piso es opcional.
- El máximo de huéspedes tiene que ser mayor a 0.
- Un departamento nuevo queda activo.

### Dar de baja un departamento

- Las reservas del departamento no se eliminan.
- Si tiene reservas futuras no canceladas, el sistema avisa y pide confirmación. Si se confirma, esas reservas se cancelan.
- No se pueden cargar reservas en un departamento dado de baja.

### Cargar una reserva

- La fecha de egreso tiene que ser posterior a la de ingreso.
- No puede superponerse con otra reserva no cancelada del mismo departamento. Se permite que una reserva empiece el mismo día en que termina otra.
- La cantidad de personas tiene que ir de 1 al máximo de huéspedes del departamento.
- Tiene una persona a cargo, con nombre obligatorio y teléfono opcional.
- Las noches se calculan a partir de las fechas; no se cargan.
- El sistema sugiere un precio igual a noches × precio por noche (este último lo carga el dueño). El dueño puede modificarlo, y la reserva guarda el precio acordado.
- La fecha de cambio de ropa blanca es opcional. Si se carga, tiene que estar entre la fecha de ingreso y la de egreso. Hay como máximo un cambio por estadía.
- Puede tener notas libres.

### Marcar una reserva como pagada

- Se guarda el medio de pago.
- Una reserva está pagada si tiene medio de pago.

### Cancelar una reserva

- Se guarda la fecha de cancelación. La reserva no se elimina.
- Las noches de una reserva cancelada quedan libres para otras reservas.

### Ver reservas

- **En curso:** reservas no canceladas con ingreso <= hoy < egreso.
- **Próximas:** reservas no canceladas con ingreso > hoy, ordenadas por fecha de ingreso.
- Las reservas canceladas no se muestran.

### Login

- Hay un único usuario, creado previamente con un comando. No hay registro.
- La contraseña se guarda hasheada.
- Se ingresa al sistema solo si el usuario y la contraseña son correctos.
- Si alguno es incorrecto, se rechaza el ingreso con un mensaje que no indica cuál de los dos falló.
- Sin iniciar sesión no se puede acceder a ninguna funcionalidad.
- Se puede cerrar sesión.

## Fuera de la v1

- Métricas (ocupación, ingresos, precio promedio por noche).
- Sincronización de reservas con Google Calendar.
- Tabla de tarifas por mes o temporada.
- Aviso automático de cambio de ropa blanca.
- Registro de la fecha de pago.
