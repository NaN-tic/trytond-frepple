from datetime import datetime
from proteus import config, Model

#frepple.printsize()

# Loading

def buffer_name(product, location):
    return '%s @ %s' % (product.rec_name, location.rec_name)

config = config.set_trytond(database_type='postgresql',
    database_name='tryton3')

# Create Customers
customers = {}
Party = Model.get('party.party')
for party in Party.find([]):
    customer = frepple.customer(name=party.rec_name, subcategory='Tryton')
    customers[party.id] = customer

# Create Items
items = {}
products = {}
Product = Model.get('product.product')
for product in Product.find([]):
    item = frepple.item(name=product.rec_name, subcategory='Tryton')
    items[product.id] = item
    products[product.id] = product

# Create Locations
locations = {}
try_locations = {}
Location = Model.get('stock.location')
for location in Location.find([]):
    loc = frepple.location(name=location.rec_name, subcategory='Tryton')
    locations[location.id] = loc
    try_locations[location.id] = location

# Create Demands
SaleLine = Model.get('sale.line')
for line in SaleLine.find([
            ('product', '!=', None),
            ]):
    item = items[line.product.id]
    location = locations[line.sale.warehouse.storage_location.id]
    customer = customers[line.sale.party.id]
    buf_name = buffer_name(line.product, line.sale.warehouse.storage_location)

    operation = frepple.operation(name=line.rec_name, subcategory='Tryton',
        location=location)
    buf = frepple.buffer(name=buf_name, subcategory='Tryton',
        item=item, location=location)
    frepple.flow(operation=operation, buffer=buf, quantity=-1,
        type='flow_start')
    frepple.demand(name=line.rec_name, subcategory='Tryton',
        item=item, customer=customer, operation=operation,
        quantity=line.quantity)

# Create onhand
quantities = Model.get('product.product').products_by_location(locations.keys(),
    items.keys(), config.context)
for key, quantity in quantities.iteritems():
    location_id = key[0]
    product_id = key[1]
    buf_name = buffer_name(products[product_id], try_locations[location_id])
    frepple.buffer(name=buf_name, subcategory='Tryton', onhand=quantity)

# Create purchases
PurchaseLine = Model.get('purchase.line')
for line in PurchaseLine.find([
            ('product', '!=', None),
            ]):
    item = items[line.product.id]
    location = locations[line.purchase.warehouse.storage_location.id]
    buf_name = buffer_name(line.product,
        line.purchase.warehouse.storage_location)
    operation_name = 'Procure for %s @ %s' % (line.product.rec_name,
        line.purchase.warehouse.storage_location.rec_name)
    buf = frepple.buffer(name=buf_name, subcategory='Tryton', item=item,
        location=location)
    operation = frepple.operation(name=operation_name, subcategory='Tryton',
        location=location)
    frepple.flow(operation=operation, buffer=buf, type='flow_end', quantity=1)
    date = line.purchase.purchase_date or datetime.now()
    frepple.operationplan(operation=operation, end=date, start=date,
        quantity=line.quantity, locked=False)

# TODO: Create resources: Resources represent capacity. They represent a
# machine, a worker or a group of workers, or some logical limits.

# TODO: Create boms

# TODO: Create setup matrices

# TODO: Create policies

# TODO:
#  - renaming an entity in OpenERP is not handled right: id remains the 
#    same in OpenERP, but the object name in frePPLe is different.
#  - Load reorder points
#  - Load loads
#  - Load WIP
#  - Unit of measures are not used


frepple.printsize()

# Parameters
plantype = 1
constraint = 15

# Solving
solver = frepple.solver_mrp(name="MRP", constraints=constraint,
      plantype=plantype, loglevel=0
      #userexit_resource=debugResource,
      #userexit_demand=debugDemand,
      )
solver.solve()
# Exporting

Simulation = Model.get('frepple.simulation')
Problem = Model.get('frepple.problem')

date = datetime.now()

simulation = Simulation()
simulation.name = unicode(date)
simulation.date = date
simulation.save()

print '-' * 60
for problem in frepple.problems():
    print 'Entity:', problem.entity
    print 'Name:', problem.name
    print 'Description:', problem.description
    print 'Start:', problem.start
    print 'End:', problem.end
    print 'Weight', problem.weight
    print '-' * 60
    p = Problem(simulation=simulation, entity=problem.entity, name=problem.name,
        description=problem.description, start=problem.start, end=problem.end,
        weight=problem.weight)
    p.save()

frepple.printsize()
