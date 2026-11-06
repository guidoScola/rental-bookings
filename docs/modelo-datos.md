# Modelo de datos v1

Tablas y columnas en inglés. Base de datos: PostgreSQL.

## apartment

| Columna | Tipo | Reglas |
|---|---|---|
| id | serial | PK |
| name | text | obligatorio |
| address | text | obligatorio |
| floor | text | opcional |
| max_guests | integer | obligatorio, `> 0` |
| deactivated_at | date | opcional; si tiene valor, el departamento está dado de baja |

## booking

| Columna | Tipo | Reglas |
|---|---|---|
| id | serial | PK |
| apartment_id | integer | obligatorio, FK → `apartment.id` |
| guest_name | text | obligatorio |
| guest_phone | text | opcional |
| guest_count | integer | obligatorio, `>= 1` |
| check_in | date | obligatorio |
| check_out | date | obligatorio, `> check_in` |
| price | numeric(10, 2) | obligatorio, `>= 0` |
| payment_method | text | opcional, `'cash'` o `'transfer'`; si tiene valor, la reserva está pagada |
| linen_change_date | date | opcional, entre `check_in` y `check_out` |
| cancelled_at | date | opcional; si tiene valor, la reserva está cancelada |
| notes | text | opcional |

## app_user

| Columna | Tipo | Reglas |
|---|---|---|
| id | serial | PK |
| username | text | obligatorio, único |
| password_hash | text | obligatorio |

La tabla se llama `app_user` porque `user` es una palabra reservada en PostgreSQL.

## Decisiones

- **Fechas opcionales en lugar de sí/no.** `deactivated_at`, `cancelled_at` y `payment_method` indican un estado y, además, cuándo ocurrió o cómo. Así no se guardan dos datos que puedan contradecirse.
- **El precio se guarda, no se calcula.** Es el precio acordado con el huésped, y no cambia si cambian las tarifas.
- **Las noches no se guardan.** Se calculan como `check_out - check_in`.
- **El huésped va dentro de la reserva.** En la v1 no hace falta el historial por huésped.
- **`numeric` y no `float` para la plata**, para evitar errores de redondeo.
- **Las estadías son intervalos semiabiertos `[check_in, check_out)`.** La noche del egreso no cuenta, así que una reserva puede empezar el día en que termina otra.
- **Superposición:** un `EXCLUDE` constraint sobre `daterange(check_in, check_out)` y `apartment_id`, que ignora las reservas canceladas.
- **`guest_count <= max_guests` y "no reservar en un departamento dado de baja" se validan en la aplicación**, porque involucran dos tablas y un `CHECK` solo puede mirar la fila propia.
