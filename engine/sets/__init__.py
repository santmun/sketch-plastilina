# sets — escenarios intercambiables. Cada módulo expone build(ctx) -> dict con:
#   seats   {nombre: dict(pos=(x,y,0), yaw=grados, chair=fn(W)->objs | None)}  asientos para humanos sentados
#   anchors {nombre: dict(pos=(x,y,z), yaw=grados|None, sigue=prop|None, eje=(x,y,z))} lugares (escondites, marcas)
#   props   {nombre: Prop}  objetos animables desde blocking.json["props"] (valor por cuadro)
#   probes  {nombre: Vector} puntos para apuntar cámaras ('set:monitor')
#   looks   {'noche': fn(SC, ctx), 'dia': fn(SC, ctx)} ajustes del set para cada look (luces prácticas, colores)
#   ambiente  'oficina' | 'cafe' | ...  (tono de sala que sintetiza mix.py)
#   publico   Vector: de qué lado está «el público» (planos generales y los que piden desde='set')
# ctx = dict(prj=Project, params=look.json["set_params"], cast=cast.json personajes)
# Convención: piso z=0, metros, la cámara principal suele estar en -Y mirando a +Y.
import importlib


def load(name):
    return importlib.import_module(f'sets.{name}')
