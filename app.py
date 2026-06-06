
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = "cambia-esta-clave-en-produccion"
DB_PATH = Path(__file__).with_name("pasteleria.db")

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

PRODUCTOS_INICIALES = [
    ("Torta de Chocolate", "Bizcocho húmedo con ganache artesanal y decoración premium.", 85.00, "torta-chocolate.svg", 1),
    ("Cupcakes Gourmet", "Caja de 6 cupcakes surtidos: vainilla, chocolate, lúcuma y fresa.", 45.00, "cupcakes.svg", 1),
    ("Cheesecake de Fresa", "Cheesecake cremoso con salsa de fresas naturales.", 75.00, "cheesecake.svg", 1),
    ("Galletas Decoradas", "Galletas de mantequilla decoradas a mano para eventos.", 35.00, "galletas.svg", 1),
    ("Macarons Franceses", "Caja de 12 macarons con sabores variados y colores pastel.", 50.00, "macarons.svg", 1),
    ("Croissants & Hojaldres", "Croissants artesanales de mantequilla, crujientes y frescos.", 8.00, "croissant.svg", 1),
]

SERVICIOS_INICIALES = [
    ("Tortas personalizadas", "Diseños para bodas, cumpleaños, bautizos y eventos corporativos."),
    ("Mesa dulce para eventos", "Armado de mesa con cupcakes, bocaditos, galletas, mini postres y decoración."),
    ("Delivery programado", "Entrega coordinada en Lima con empaque seguro y presentación elegante."),
]

CLIENTES_INICIALES = [
    ("María Pérez", "maria@email.com", "999111222"),
    ("Carlos Ramírez", "carlos@email.com", "988555444"),
]


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_conn() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS servicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL,
            telefono TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'cliente'
        );
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            correo TEXT NOT NULL,
            telefono TEXT NOT NULL,
            direccion TEXT NOT NULL,
            metodo_pago TEXT NOT NULL,
            total REAL NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        if conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
            conn.executemany("INSERT INTO productos(nombre, descripcion, precio, imagen, activo) VALUES(?,?,?,?,?)", PRODUCTOS_INICIALES)
        if conn.execute("SELECT COUNT(*) FROM servicios").fetchone()[0] == 0:
            conn.executemany("INSERT INTO servicios(nombre, descripcion) VALUES(?,?)", SERVICIOS_INICIALES)
        if conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0] == 0:
            conn.executemany("INSERT INTO clientes(nombre, correo, telefono) VALUES(?,?,?)", CLIENTES_INICIALES)
        admin = conn.execute("SELECT id FROM usuarios WHERE correo=?", (ADMIN_USER,)).fetchone()
        if admin is None:
            conn.execute("INSERT INTO usuarios(nombre, correo, password, rol) VALUES(?,?,?,?)", ("Administrador", ADMIN_USER, ADMIN_PASS, "admin"))
        conn.commit()


@app.before_request
def asegurar_db():
    init_db()


def obtener_productos(activos=True):
    with db_conn() as conn:
        if activos:
            return conn.execute("SELECT * FROM productos WHERE activo=1 ORDER BY id DESC").fetchall()
        return conn.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()


def obtener_servicios():
    with db_conn() as conn:
        return conn.execute("SELECT * FROM servicios ORDER BY id DESC").fetchall()


def obtener_clientes():
    with db_conn() as conn:
        return conn.execute("SELECT * FROM clientes ORDER BY id DESC").fetchall()


def carrito_actual():
    return session.setdefault("carrito", {})


def total_carrito():
    cart = carrito_actual()
    total = 0
    items = []
    with db_conn() as conn:
        for id_txt, cantidad in cart.items():
            producto = conn.execute("SELECT * FROM productos WHERE id=?", (id_txt,)).fetchone()
            if producto:
                subtotal = producto["precio"] * int(cantidad)
                total += subtotal
                items.append({"producto": producto, "cantidad": int(cantidad), "subtotal": subtotal})
    return items, total


def admin_requerido(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("rol") != "admin":
            flash("Acceso restringido. Inicia sesión como administrador.", "error")
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


def cliente_requerido(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("rol") not in ["cliente", "admin"]:
            flash("Primero inicia sesión o regístrate.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return render_template("index.html", productos=obtener_productos(), servicios=obtener_servicios())

@app.route("/productos")
def productos_publicos():
    return render_template("productos.html", productos=obtener_productos())

@app.route("/carrito")
def carrito():
    items, total = total_carrito()
    return render_template("carrito.html", items=items, total=total)

@app.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    cantidad = max(1, int(request.form.get("cantidad", 1)))
    cart = carrito_actual()
    cart[str(producto_id)] = int(cart.get(str(producto_id), 0)) + cantidad
    session["carrito"] = cart
    flash("Producto agregado al carrito.", "ok")
    return redirect(request.referrer or url_for("productos_publicos"))

@app.route("/carrito/actualizar", methods=["POST"])
def actualizar_carrito():
    cart = {}
    for key, value in request.form.items():
        if key.startswith("cantidad_"):
            pid = key.replace("cantidad_", "")
            try:
                cantidad = int(value)
            except ValueError:
                cantidad = 1
            if cantidad > 0:
                cart[pid] = cantidad
    session["carrito"] = cart
    flash("Carrito actualizado.", "ok")
    return redirect(url_for("carrito"))

@app.route("/carrito/eliminar/<int:producto_id>", methods=["POST"])
def eliminar_carrito(producto_id):
    cart = carrito_actual()
    cart.pop(str(producto_id), None)
    session["carrito"] = cart
    flash("Producto eliminado del carrito.", "ok")
    return redirect(url_for("carrito"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = total_carrito()
    if not items:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for("productos_publicos"))
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        telefono = request.form.get("telefono", "").strip()
        direccion = request.form.get("direccion", "").strip()
        metodo = request.form.get("metodo_pago", "Tarjeta demo")
        if not all([nombre, correo, telefono, direccion]):
            flash("Completa todos los datos para procesar el pedido.", "error")
            return redirect(url_for("checkout"))
        with db_conn() as conn:
            conn.execute("INSERT INTO pedidos(cliente, correo, telefono, direccion, metodo_pago, total) VALUES(?,?,?,?,?,?)", (nombre, correo, telefono, direccion, metodo, total))
            conn.execute("INSERT INTO clientes(nombre, correo, telefono) VALUES(?,?,?)", (nombre, correo, telefono))
            conn.commit()
        session["carrito"] = {}
        return render_template("pago_exitoso.html", nombre=nombre, total=total, metodo=metodo)
    return render_template("checkout.html", items=items, total=total)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        with db_conn() as conn:
            user = conn.execute("SELECT * FROM usuarios WHERE correo=? AND password=? AND rol='cliente'", (correo, password)).fetchone()
        if user:
            session.clear()
            session["usuario_id"] = user["id"]
            session["usuario_nombre"] = user["nombre"]
            session["rol"] = "cliente"
            flash("Bienvenido/a, " + user["nombre"] + ".", "ok")
            return redirect(url_for("home"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar", "")
        telefono = request.form.get("telefono", "").strip()
        if not nombre or not correo or not password:
            flash("Completa todos los campos obligatorios.", "error")
            return redirect(url_for("registro"))
        if password != confirmar:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for("registro"))
        try:
            with db_conn() as conn:
                conn.execute("INSERT INTO usuarios(nombre, correo, password, rol) VALUES(?,?,?,?)", (nombre, correo, password, "cliente"))
                conn.execute("INSERT INTO clientes(nombre, correo, telefono) VALUES(?,?,?)", (nombre, correo, telefono or "No registrado"))
                conn.commit()
        except sqlite3.IntegrityError:
            flash("Ese correo ya está registrado.", "error")
            return redirect(url_for("registro"))
        flash("Cuenta creada. Ahora inicia sesión.", "ok")
        return redirect(url_for("login"))
    return render_template("registro.html")

@app.route("/mi-cuenta")
@cliente_requerido
def mi_cuenta():
    return render_template("mi_cuenta.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("home"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        if usuario == ADMIN_USER and password == ADMIN_PASS:
            session.clear()
            session["usuario_nombre"] = "Administrador"
            session["rol"] = "admin"
            session["admin"] = True
            flash("Bienvenido al panel administrador.", "ok")
            return redirect(url_for("admin_dashboard"))
        flash("Usuario o contraseña de administrador incorrectos.", "error")
    return render_template("admin_login.html")

@app.route("/admin")
@admin_requerido
def admin_dashboard():
    with db_conn() as conn:
        pedidos = conn.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 8").fetchall()
    return render_template("admin/dashboard.html", productos=obtener_productos(False), servicios=obtener_servicios(), clientes=obtener_clientes(), pedidos=pedidos)

@app.route("/admin/productos/nuevo", methods=["GET", "POST"])
@admin_requerido
def producto_nuevo():
    if request.method == "POST":
        with db_conn() as conn:
            conn.execute("INSERT INTO productos(nombre, descripcion, precio, imagen, activo) VALUES(?,?,?,?,?)", (request.form["nombre"], request.form["descripcion"], float(request.form["precio"]), request.form.get("imagen") or "torta-chocolate.svg", int(request.form.get("activo", 1))))
            conn.commit()
        flash("Producto creado.", "ok")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/producto_form.html", producto=None)

@app.route("/admin/productos/editar/<int:id>", methods=["GET", "POST"])
@admin_requerido
def producto_editar(id):
    with db_conn() as conn:
        producto = conn.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
        if request.method == "POST":
            conn.execute("UPDATE productos SET nombre=?, descripcion=?, precio=?, imagen=?, activo=? WHERE id=?", (request.form["nombre"], request.form["descripcion"], float(request.form["precio"]), request.form.get("imagen") or producto["imagen"], int(request.form.get("activo", 0)), id))
            conn.commit()
            flash("Producto actualizado.", "ok")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/producto_form.html", producto=producto)

@app.route("/admin/productos/eliminar/<int:id>", methods=["POST"])
@admin_requerido
def producto_eliminar(id):
    with db_conn() as conn:
        conn.execute("DELETE FROM productos WHERE id=?", (id,))
        conn.commit()
    flash("Producto eliminado.", "ok")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/servicios/nuevo", methods=["GET", "POST"])
@admin_requerido
def servicio_nuevo():
    if request.method == "POST":
        with db_conn() as conn:
            conn.execute("INSERT INTO servicios(nombre, descripcion) VALUES(?,?)", (request.form["nombre"], request.form["descripcion"]))
            conn.commit()
        flash("Servicio creado.", "ok")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/servicio_form.html", servicio=None)

@app.route("/admin/servicios/editar/<int:id>", methods=["GET", "POST"])
@admin_requerido
def servicio_editar(id):
    with db_conn() as conn:
        servicio = conn.execute("SELECT * FROM servicios WHERE id=?", (id,)).fetchone()
        if request.method == "POST":
            conn.execute("UPDATE servicios SET nombre=?, descripcion=? WHERE id=?", (request.form["nombre"], request.form["descripcion"], id))
            conn.commit()
            flash("Servicio actualizado.", "ok")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/servicio_form.html", servicio=servicio)

@app.route("/admin/servicios/eliminar/<int:id>", methods=["POST"])
@admin_requerido
def servicio_eliminar(id):
    with db_conn() as conn:
        conn.execute("DELETE FROM servicios WHERE id=?", (id,))
        conn.commit()
    flash("Servicio eliminado.", "ok")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/clientes/nuevo", methods=["GET", "POST"])
@admin_requerido
def cliente_nuevo():
    if request.method == "POST":
        with db_conn() as conn:
            conn.execute("INSERT INTO clientes(nombre, correo, telefono) VALUES(?,?,?)", (request.form["nombre"], request.form["correo"], request.form["telefono"]))
            conn.commit()
        flash("Cliente creado.", "ok")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/cliente_form.html", cliente=None)

@app.route("/admin/clientes/editar/<int:id>", methods=["GET", "POST"])
@admin_requerido
def cliente_editar(id):
    with db_conn() as conn:
        cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
        if request.method == "POST":
            conn.execute("UPDATE clientes SET nombre=?, correo=?, telefono=? WHERE id=?", (request.form["nombre"], request.form["correo"], request.form["telefono"], id))
            conn.commit()
            flash("Cliente actualizado.", "ok")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/cliente_form.html", cliente=cliente)

@app.route("/admin/clientes/eliminar/<int:id>", methods=["POST"])
@admin_requerido
def cliente_eliminar(id):
    with db_conn() as conn:
        conn.execute("DELETE FROM clientes WHERE id=?", (id,))
        conn.commit()
    flash("Cliente eliminado.", "ok")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
