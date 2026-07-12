# Instrucciones de Integración - Vista de Tareas

## 📋 Resumen

Se ha agregado exitosamente una nueva vista **"Tareas"** a tu aplicación Streamlit con las siguientes características:

- ✅ Panel de métricas (6 indicadores clave)
- ✅ 3 gráficos estadísticos interactivos
- ✅ Tabla filtrable y buscable
- ✅ Formulario para crear nuevas tareas (solo admin)
- ✅ Script SQL con 100 tareas de ejemplo

---

## 🚀 Paso 1: Insertar Datos de Ejemplo en Supabase

### Opción A: Usando el SQL Editor de Supabase (Recomendado)

1. **Accede a tu proyecto en Supabase**
   - Ve a [https://app.supabase.com](https://app.supabase.com)
   - Selecciona tu proyecto

2. **Abre el SQL Editor**
   - En el menú lateral, haz clic en **"SQL Editor"**
   - Haz clic en **"New query"**

3. **Ejecuta el script**
   - Abre el archivo: `querys para supabase/insert_sample_tasks.sql`
   - Copia TODO el contenido del archivo
   - Pégalo en el editor SQL de Supabase
   - Haz clic en **"Run"** o presiona `Ctrl + Enter`

4. **Verifica la inserción**
   - Deberías ver un mensaje: `"Se insertaron 100 tareas exitosamente"`
   - También verás un resumen con estadísticas de las tareas insertadas

5. **Confirma en la tabla**
   - Ve a **"Table Editor"** en el menú lateral
   - Selecciona la tabla **"tareas"**
   - Deberías ver aproximadamente 100 nuevas filas

### Opción B: Verificación Manual

Si ya tienes reuniones y usuarios en tu base de datos, el script funcionará automáticamente. Si no:

```sql
-- Primero verifica que tengas reuniones
SELECT COUNT(*) FROM reuniones;

-- Verifica que tengas usuarios
SELECT COUNT(*) FROM usuarios;
```

Si alguna de estas consultas devuelve 0, necesitas crear reuniones y usuarios primero antes de ejecutar el script de tareas.

---

## 🎯 Paso 2: Probar la Nueva Vista

### 1. Ejecuta la aplicación

```powershell
cd "d:\UNI 2025\8VO CICLO\Nueva carpeta\zoom2\zoom2"
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

### 2. Inicia sesión

- Usa tus credenciales existentes
- La aplicación abrirá en tu navegador (generalmente `http://localhost:8501`)

### 3. Navega a "Tareas"

- En el menú lateral (sidebar), verás la nueva opción **"Tareas"**
- Haz clic en ella

### 4. Explora las funcionalidades

**Panel de Métricas** (parte superior):
- Total Tareas
- Completadas (con % de avance)
- Pendientes
- En Progreso
- Atrasadas (con indicador visual)
- % Avance general

**Gráficos Estadísticos**:
- **Izquierda**: Tareas por estado (gráfico de barras con colores)
- **Centro**: Tareas por usuario asignado (gráfico circular)
- **Derecha**: Creación de tareas por semana (gráfico de línea)

**Filtros**:
- Búsqueda por texto en descripción
- Filtro por estado (pendiente, en_progreso, completada)
- Filtro por usuario asignado

**Tabla de Tareas**:
- Muestra todas las tareas con sus detalles
- Si eres admin, puedes editar el estado y asignación directamente
- Haz clic en "💾 Guardar cambios" para persistir las ediciones

**Crear Nueva Tarea** (solo admin):
- Formulario al final de la página
- Selecciona una reunión existente
- Completa la descripción
- Asigna a un usuario (opcional)
- Selecciona el estado
- Define la fecha de vencimiento
- Haz clic en "Crear tarea"

---

## 🔧 Cambios Realizados en el Código

### Archivo: `app.py`

**1. Nueva función agregada** (línea ~1120):
```python
def view_tareas():
    # Función completa con métricas, gráficos, filtros y tabla
```

**2. Navegación actualizada** (línea ~1507):
```python
opciones_menu = ["Chat", "Reuniones", "Tareas", "Resumen de reuniones", "Participantes", "Cerrar sesión"]
```

**3. Routing agregado** (línea ~1517):
```python
elif page == "Tareas":
    view_tareas()
```

### Archivo nuevo: `querys para supabase/insert_sample_tasks.sql`

Script SQL que inserta 100 tareas con:
- Descripciones realistas de tareas empresariales
- Estados distribuidos: 40% pendiente, 30% en progreso, 30% completada
- 80% asignadas a usuarios existentes, 20% sin asignar
- Fechas de vencimiento: 20% vencidas, 50% próximas (0-30 días), 30% futuras (30-90 días)
- Fechas de creación distribuidas en los últimos 60 días

---

## 📊 Estructura de Datos

La vista "Tareas" utiliza la tabla `tareas` con la siguiente estructura:

```sql
tareas (
  id uuid PRIMARY KEY,
  reunion_id uuid REFERENCES reuniones(id),
  descripcion text NOT NULL,
  asignado_a_correo varchar(255),
  estado varchar(20) DEFAULT 'pendiente',
  fecha_vencimiento timestamp with time zone,
  fecha_creacion timestamp with time zone DEFAULT now()
)
```

**Estados válidos**: `pendiente`, `en_progreso`, `completada`

---

## 🎨 Características de la Vista

### Métricas Calculadas

1. **Total Tareas**: Cuenta total de registros
2. **Completadas**: Tareas con estado = 'completada'
3. **Pendientes**: Tareas con estado = 'pendiente'
4. **En Progreso**: Tareas con estado = 'en_progreso'
5. **Atrasadas**: Tareas con fecha_vencimiento < hoy Y estado ≠ 'completada'
6. **% Avance**: (Completadas / Total) × 100

### Gráficos Interactivos

Todos los gráficos son interactivos (hover para ver detalles):

- **Barras**: Muestra distribución por estado con colores distintivos
- **Circular**: Top 10 usuarios con más tareas asignadas
- **Línea**: Tendencia de creación de tareas por semana

### Filtros Dinámicos

- **Búsqueda**: Busca en el campo descripción (case-insensitive)
- **Estado**: Filtra por pendiente, en_progreso, completada, o "Todos"
- **Asignado**: Filtra por usuario específico o "Todos"

Los filtros se aplican en tiempo real y muestran el contador de resultados.

---

## 🔐 Permisos

- **Usuarios normales**: Solo pueden VER las tareas
- **Administradores** (juanaureliodelacruzgamarra@gmail.com):
  - Pueden EDITAR tareas existentes (estado, asignación, descripción)
  - Pueden CREAR nuevas tareas
  - Pueden GUARDAR cambios en la base de datos

---

## ⚠️ Solución de Problemas

### Error: "No hay tareas registradas"

**Causa**: La tabla `tareas` está vacía.

**Solución**: Ejecuta el script SQL `insert_sample_tasks.sql` en Supabase.

---

### Error: "No hay reuniones en la base de datos"

**Causa**: El script SQL requiere reuniones existentes.

**Solución**: 
1. Ve a la vista "Reuniones" en la app
2. Crea al menos una reunión
3. Luego ejecuta el script SQL de tareas

---

### Error al cargar tareas

**Causa**: Problema de conexión con Supabase o credenciales incorrectas.

**Solución**:
1. Verifica tu archivo `.env`:
   ```
   SUPABASE_URL=https://tu-proyecto.supabase.co
   SUPABASE_ANON_KEY=tu-clave-anon
   ```
2. Reinicia la aplicación Streamlit

---

### Los gráficos no se muestran

**Causa**: Datos insuficientes o error en Altair.

**Solución**: Verifica que tengas al menos 5-10 tareas en la base de datos.

---

## 📝 Notas Adicionales

1. **Dependencias**: No se requieren nuevas dependencias. La vista usa las librerías ya instaladas:
   - `streamlit`
   - `pandas`
   - `altair`
   - `requests`

2. **Rendimiento**: La vista está optimizada para manejar cientos de tareas. Si tienes miles, considera agregar paginación.

3. **Personalización**: Puedes modificar:
   - Colores de los gráficos (busca `scale=alt.Scale`)
   - Descripciones en el script SQL
   - Campos editables en la tabla

4. **Seguridad**: Las ediciones solo se permiten a usuarios admin. El correo admin está hardcodeado en la función `is_admin()`.

---

## ✅ Checklist de Verificación

- [ ] Script SQL ejecutado exitosamente en Supabase
- [ ] 100 tareas visibles en Table Editor de Supabase
- [ ] Aplicación Streamlit ejecutándose sin errores
- [ ] Opción "Tareas" visible en el menú de navegación
- [ ] Panel de métricas mostrando datos correctos
- [ ] Los 3 gráficos se renderizan correctamente
- [ ] Filtros funcionan al cambiar valores
- [ ] Tabla muestra todas las tareas
- [ ] (Admin) Formulario de creación funciona
- [ ] (Admin) Edición y guardado de cambios funciona

---

## 🎉 ¡Listo!

Tu aplicación ahora tiene una vista completa de gestión de tareas con métricas, gráficos y análisis estadístico. 

Si tienes alguna pregunta o necesitas personalizar algo, no dudes en preguntar.
