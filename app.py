# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'clave_secreta_biblioteca_2024'  # Necesaria para las sesiones

# ----------------- CONEXIÓN A MONGODB -----------------
try:
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    client.admin.command('ping') 

    # Base de datos y colecciones - USANDO TU BASE DE DATOS EXISTENTE
    db = client['libros']            # Tu base de datos existente
    
    # Colecciones
    coleccion_libros = db['tipolibro']     # Tu colección existente
    coleccion_usuarios = db['usuarios']    # Nueva colección
    coleccion_clientes = db['clientes']    # Nueva colección  
    coleccion_ventas = db['ventas']        # Nueva colección

    print("Conexión exitosa a MongoDB.")

except Exception as e:
    print(f"ERROR: No se pudo conectar a MongoDB. Detalle: {e}")

# ----------------- FUNCIÓN PARA ENCRIPTAR CONTRASEÑAS -----------------
def encriptar_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------- MIDDLEWARE DE AUTENTICACIÓN -----------------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- RUTA PARA CREAR USUARIO DEMO -----------------
@app.route('/crear-usuario-demo')
def crear_usuario_demo():
    try:
        # Verificar si ya existe
        usuario_existente = coleccion_usuarios.find_one({'email': 'admin@biblioteca.com'})
        if usuario_existente:
            return "El usuario demo ya existe. Usa: admin@biblioteca.com / admin123"
        
        # Crear usuario demo
        usuario_demo = {
            'nombre': 'Administrador Principal',
            'email': 'admin@biblioteca.com',
            'password': encriptar_password('admin123'),
            'rol': 'administrador',
            'fecha_creacion': datetime.now(),
            'activo': True
        }
        
        coleccion_usuarios.insert_one(usuario_demo)
        return """
        <h1>Usuario demo creado exitosamente</h1>
        <p><strong>Email:</strong> admin@biblioteca.com</p>
        <p><strong>Contraseña:</strong> admin123</p>
        <p><a href="/login">Ir al Login</a></p>
        """
    except Exception as e:
        return f"Error: {e}"

# ----------------- RUTAS DE AUTENTICACIÓN -----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        usuario = coleccion_usuarios.find_one({
            'email': email, 
            'password': encriptar_password(password),
            'activo': True
        })
        
        if usuario:
            session['usuario_id'] = str(usuario['_id'])
            session['usuario_nombre'] = usuario['nombre']
            session['usuario_rol'] = usuario['rol']
            flash('¡Bienvenido ' + usuario['nombre'] + '!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas. Intenta con admin@biblioteca.com / admin123', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('login'))

# ----------------- RUTAS PRINCIPALES -----------------

@app.route('/')
@login_required
def index():
    try:
        libros = coleccion_libros.find()
        return render_template('index.html', libros=libros)
    except Exception as e:
        print(f"Error en la ruta INDEX: {e}")
        return "<h1>Error al cargar la Base de Datos</h1>", 500

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Estadísticas para el dashboard
        total_libros = coleccion_libros.count_documents({})
        total_clientes = coleccion_clientes.count_documents({})
        total_ventas = coleccion_ventas.count_documents({})
        
        # Ventas del mes
        inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ventas_mes = list(coleccion_ventas.find({'fecha_venta': {'$gte': inicio_mes}}))
        total_ventas_mes = sum(venta.get('total', 0) for venta in ventas_mes)
        
        # Libros con stock bajo
        libros_stock_bajo = list(coleccion_libros.find({'stock': {'$lt': 5}}))
        
        return render_template('dashboard.html',
                             total_libros=total_libros,
                             total_clientes=total_clientes,
                             total_ventas=total_ventas,
                             total_ventas_mes=total_ventas_mes,
                             libros_stock_bajo=libros_stock_bajo)
    except Exception as e:
        flash(f'Error al cargar dashboard: {e}', 'error')
        return render_template('dashboard.html')

# ----------------- CRUD LIBROS -----------------

@app.route('/agregar', methods=['GET'])
@login_required
def agregar():
    return render_template('agregar.html')

@app.route('/crear', methods=['POST'])
@login_required
def crear():
    try:
        libro = {
            'nombre': request.form.get('nombre'),         
            'autor': request.form.get('autor'),
            'genero': request.form.get('genero'),         
            'stock': request.form.get('stock', type=int), 
            'isbn': request.form.get('isbn'),
            'anio_publicacion': request.form.get('anio_publicacion', type=int),
            'precio': float(request.form.get('precio', 0)),
            'fecha_agregado': datetime.now()
        }
        coleccion_libros.insert_one(libro)
        flash('Libro agregado exitosamente', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error al crear el libro: {e}', 'error')
        return redirect(url_for('agregar'))

@app.route('/editar/<id>')
@login_required
def editar(id):
    try:
        libro = coleccion_libros.find_one({'_id': ObjectId(id)})
        if libro:
            return render_template('editar.html', libro=libro)
        else:
            flash('Libro no encontrado', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error al cargar el formulario de edición: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/actualizar/<id>', methods=['POST'])
@login_required
def actualizar(id):
    try:
        datos_actualizados = {
            'nombre': request.form.get('nombre'),         
            'autor': request.form.get('autor'),
            'genero': request.form.get('genero'),
            'stock': request.form.get('stock', type=int),
            'isbn': request.form.get('isbn'),
            'anio_publicacion': request.form.get('anio_publicacion', type=int),
            'precio': float(request.form.get('precio', 0))
        }
        
        coleccion_libros.update_one(
            {'_id': ObjectId(id)},
            {'$set': datos_actualizados}
        )
        flash('Libro actualizado exitosamente', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error al actualizar el libro: {e}', 'error')
        return redirect(url_for('editar', id=id))

@app.route('/eliminar/<id>', methods=['POST'])
@login_required
def eliminar(id):
    try:
        coleccion_libros.delete_one({'_id': ObjectId(id)})
        flash('Libro eliminado exitosamente', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error al eliminar el libro: {e}', 'error')
        return redirect(url_for('index'))

# ----------------- CRUD CLIENTES -----------------

@app.route('/clientes')
@login_required
def listar_clientes():
    try:
        clientes = coleccion_clientes.find()
        return render_template('clientes.html', clientes=clientes)
    except Exception as e:
        flash(f'Error al cargar clientes: {e}', 'error')
        return render_template('clientes.html', clientes=[])

@app.route('/clientes/agregar', methods=['GET', 'POST'])
@login_required
def agregar_cliente():
    if request.method == 'POST':
        try:
            cliente = {
                'nombre': request.form.get('nombre'),
                'email': request.form.get('email'),
                'telefono': request.form.get('telefono'),
                'direccion': {
                    'calle': request.form.get('calle'),
                    'ciudad': request.form.get('ciudad'),
                    'codigo_postal': request.form.get('codigo_postal')
                },
                'fecha_registro': datetime.now(),
                'activo': True
            }
            coleccion_clientes.insert_one(cliente)
            flash('Cliente agregado exitosamente', 'success')
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            flash(f'Error al agregar cliente: {e}', 'error')
    
    return render_template('agregar_cliente.html')

@app.route('/clientes/editar/<id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    try:
        cliente = coleccion_clientes.find_one({'_id': ObjectId(id)})
        
        if request.method == 'POST':
            datos_actualizados = {
                'nombre': request.form.get('nombre'),
                'email': request.form.get('email'),
                'telefono': request.form.get('telefono'),
                'direccion': {
                    'calle': request.form.get('calle'),
                    'ciudad': request.form.get('ciudad'),
                    'codigo_postal': request.form.get('codigo_postal')
                }
            }
            
            coleccion_clientes.update_one(
                {'_id': ObjectId(id)},
                {'$set': datos_actualizados}
            )
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('listar_clientes'))
        
        return render_template('editar_cliente.html', cliente=cliente)
    
    except Exception as e:
        flash(f'Error: {e}', 'error')
        return redirect(url_for('listar_clientes'))

@app.route('/clientes/eliminar/<id>', methods=['POST'])
@login_required
def eliminar_cliente(id):
    try:
        coleccion_clientes.delete_one({'_id': ObjectId(id)})
        flash('Cliente eliminado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar cliente: {e}', 'error')
    
    return redirect(url_for('listar_clientes'))

# ----------------- CRUD VENTAS -----------------

@app.route('/ventas')
@login_required
def listar_ventas():
    try:
        # Obtener ventas con información de cliente y libros
        ventas = list(coleccion_ventas.find().sort('fecha_venta', -1))
        
        # Enriquecer los datos para mostrar en la vista
        for venta in ventas:
            cliente = coleccion_clientes.find_one({'_id': ObjectId(venta['cliente_id'])})
            venta['cliente_nombre'] = cliente['nombre'] if cliente else 'Cliente no encontrado'
            
            # Calcular total si no existe
            if 'total' not in venta:
                venta['total'] = sum(item['subtotal'] for item in venta['items'])
        
        return render_template('ventas.html', ventas=ventas)
    except Exception as e:
        flash(f'Error al cargar ventas: {e}', 'error')
        return render_template('ventas.html', ventas=[])

@app.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_venta():
    if request.method == 'POST':
        try:
            cliente_id = request.form.get('cliente_id')
            items = []
            
            # Procesar items de la venta
            libro_ids = request.form.getlist('libro_id[]')
            cantidades = request.form.getlist('cantidad[]')
            
            total_venta = 0
            
            for i, libro_id in enumerate(libro_ids):
                if libro_id and cantidades[i]:
                    cantidad = int(cantidades[i])
                    libro = coleccion_libros.find_one({'_id': ObjectId(libro_id)})
                    
                    if libro and libro['stock'] >= cantidad:
                        precio = libro.get('precio', 0)
                        subtotal = precio * cantidad
                        total_venta += subtotal
                        
                        items.append({
                            'libro_id': libro_id,
                            'titulo': libro['nombre'],
                            'cantidad': cantidad,
                            'precio_unitario': precio,
                            'subtotal': subtotal
                        })
                        
                        # Actualizar stock
                        nuevo_stock = libro['stock'] - cantidad
                        coleccion_libros.update_one(
                            {'_id': ObjectId(libro_id)},
                            {'$set': {'stock': nuevo_stock}}
                        )
                    else:
                        libro_nombre = libro['nombre'] if libro else 'Libro desconocido'
                        flash(f'Stock insuficiente para {libro_nombre}', 'error')
                        return redirect(url_for('nueva_venta'))
            
            # Crear registro de venta
            venta = {
                'cliente_id': cliente_id,
                'usuario_id': session['usuario_id'],
                'items': items,
                'total': total_venta,
                'fecha_venta': datetime.now(),
                'estado': 'completada'
            }
            
            coleccion_ventas.insert_one(venta)
            flash('Venta registrada exitosamente', 'success')
            return redirect(url_for('listar_ventas'))
            
        except Exception as e:
            flash(f'Error al procesar venta: {e}', 'error')
    
    # GET: Mostrar formulario de nueva venta
    clientes = coleccion_clientes.find({'activo': True})
    libros = coleccion_libros.find({'stock': {'$gt': 0}})
    return render_template('nueva_venta.html', clientes=clientes, libros=libros)

# ----------------- INICIALIZACIÓN -----------------

if __name__ == '__main__':
    app.run(debug=True)