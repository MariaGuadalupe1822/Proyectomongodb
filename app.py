# app.py

from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId # Necesario para manejar los IDs únicos de MongoDB

app = Flask(__name__)

# ----------------- CONEXIÓN A MONGODB -----------------
try:
    # 1. Conexión al cliente
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    client.admin.command('ping') # Intenta hacer un ping para verificar la conexión

    # 2. Selección de DB y Colección
    db = client['libros']           
    coleccion = db['tipolibro']     

    print("Conexión exitosa a MongoDB.")

except Exception as e:
    print(f"ERROR: No se pudo conectar a MongoDB. Asegúrate de que 'mongod' esté corriendo. Detalle: {e}")
    # Si la conexión falla, las rutas fallarán, pero la app.py aún intentará iniciar.

# ----------------- RUTAS CRUD -----------------

# 1. READ: Mostrar todos los libros (Ruta principal '/')
@app.route('/')
def index():
    try:
        # Busca todos los documentos
        libros = coleccion.find() 
        # Renderiza la plantilla templates/index.html
        return render_template('index.html', libros=libros)
    except Exception as e:
        # Esto atrapará un error si la conexión a Mongo falló al iniciar.
        print(f"Error en la ruta INDEX: {e}")
        return "<h1>Error al cargar la Base de Datos</h1><p>Verifica que el servidor 'mongod' esté activo.</p>", 500


# 2. CREATE (Parte 1: GET): Muestra el formulario para agregar
@app.route('/agregar', methods=['GET'])
def agregar():
    return render_template('agregar.html')

# 2. CREATE (Parte 2: POST): Recibe los datos y guarda en MongoDB
@app.route('/crear', methods=['POST'])
def crear():
    try:
        libro = {
            'titulo': request.form.get('titulo'),
            'autor': request.form.get('autor'),
            'isbn': request.form.get('isbn'),
            'anio_publicacion': request.form.get('anio_publicacion', type=int) 
        }
        coleccion.insert_one(libro)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error al crear el libro: {e}", 500


# 3. UPDATE (Parte 1: GET): Muestra el formulario con datos existentes
@app.route('/editar/<id>')
def editar(id):
    try:
        # Buscar el libro por su ID. ObjectId(id) convierte el string en el formato de MongoDB.
        libro = coleccion.find_one({'_id': ObjectId(id)})
        
        if libro:
            return render_template('editar.html', libro=libro)
        else:
            return "Libro no encontrado", 404
    except Exception as e:
        return f"Error al cargar el formulario de edición: {e}", 500


# 3. UPDATE (Parte 2: POST): Recibe los datos y actualiza en MongoDB
@app.route('/actualizar/<id>', methods=['POST'])
def actualizar(id):
    try:
        datos_actualizados = {
            'titulo': request.form.get('titulo'),
            'autor': request.form.get('autor'),
            'isbn': request.form.get('isbn'),
            'anio_publicacion': request.form.get('anio_publicacion', type=int)
        }
        
        # Actualiza el documento
        coleccion.update_one(
            {'_id': ObjectId(id)},
            {'$set': datos_actualizados}
        )
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error al actualizar el libro: {e}", 500

# 4. DELETE: Eliminar Libro
@app.route('/eliminar/<id>', methods=['POST'])
def eliminar(id):
    try:
        coleccion.delete_one({'_id': ObjectId(id)})
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error al eliminar el libro: {e}", 500

# ----------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)