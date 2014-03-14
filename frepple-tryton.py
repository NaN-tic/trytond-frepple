from freppledb.execute.export_database_static import exportfrepple
from datetime import datetime
from dateutil.relativedelta import relativedelta
from proteus import config, Model
import json
import os

params = {}
param = os.environ['FREPPLE_TRYTON_PARAM']
if param:
    params = json.loads(param)

# Expected parameters:
#
# database: database name
# plan: should be 'constrained' or 'unconstrained'
# lead_time: boolean
# material: boolean
# capacity: boolean
# release_fence: boolean

def buffer_name(product, location):
    'Returns the buffer name to be used by the given product and location'
    return '%s @ %s' % (product.rec_name, location.rec_name)

def print_problems():
    print '-' * 60
    for problem in frepple.problems():
        print 'Entity:', problem.entity
        print 'Name:', problem.name
        print 'Description:', problem.description
        print 'Start:', problem.start
        print 'End:', problem.end
        print 'Weight', problem.weight
        print '-' * 60

def save_simulation():
    'Stores the simulation and its problems to the Tryton database'
    Simulation = Model.get('frepple.simulation')
    Problem = Model.get('frepple.problem')

    date = datetime.now()

    simulation = Simulation()
    simulation.name = unicode(date)
    simulation.date = date
    simulation.save()

    for problem in frepple.problems():
        p = Problem(simulation=simulation, entity=problem.entity,
            name=problem.name, description=problem.description,
            start=problem.start, end=problem.end, weight=problem.weight)
        p.save()

config = config.set_trytond(database_type='postgresql',
    database_name=params['database'])

# Create Customers
customers = {}
Party = Model.get('party.party')
for party in Party.find([]):
    customer = frepple.customer(name=party.rec_name)
    customers[party.id] = customer

# Create Locations
all_locations = {}
locations = {}
try_locations = {}
Location = Model.get('stock.location')
for location in Location.find([]):
    loc = frepple.location(name=location.rec_name)
    if location.type == 'storage':
        locations[location.id] = loc
    all_locations[location.id] = loc
    try_locations[location.id] = location

# Create Items
items = {}
products = {}
boms = []
all_operations = []
Product = Model.get('product.product')
for product in Product.find([]):
    item = frepple.item(name=product.rec_name)
    items[product.id] = item
    products[product.id] = product
    purchasable = product.template.purchasable
    if hasattr(product, 'purchasable'):
        purchasable = product.purchasable

    tryton_location = Location.find([('type', '=', 'storage')])[0]
    operations = []
    buffers_to_fill = []
    if purchasable:
        product_suppliers = product.template.product_suppliers
        if hasattr(product, 'product_suppliers'):
            product_suppliers = product.product_suppliers
        for product_supplier in product_suppliers:
            location = product_supplier.party.supplier_location
            buf_name = buffer_name(product, location)
            buffer = frepple.buffer(name=buf_name, item=item,
                location=all_locations[
                    product_supplier.party.supplier_location.id],
                size_minimum=1.0, mininventory=0.0, maxinventory=0.0)
            buffers_to_fill.append(buffer)
            operation = u'%s (#%d)' % (product_supplier.party.rec_name,
                product_supplier.id)
            operation = frepple.operation_fixed_time(name=operation,
                location=locations[tryton_location.id])
            operations.append(operation)
            frepple.flow(operation=operation, buffer=buffer, type='flow_end')

    for bom_item in product.boms:
        bom = bom_item.bom
        location = locations[tryton_location.id]
        operation = u'%s (#%d) @ %s' % (bom.rec_name, bom.id,
            tryton_location.rec_name)
        operation = frepple.operation(name=operation, location=location,
            size_multiple=1.0)
        operations.append(operation)
        # Store to process later because we need all the items created before
        # we can add them to a bom
        boms.append({
                'bom': bom,
                'location': location,
                'operation': operation,
                'tryton_location': tryton_location,
                })

    if operations:
        operation = u'%s (#%d)' % (product.rec_name, product.id)
        operation = frepple.operation_alternate(name=operation)
        priority = 0
        for suboperation in operations:
            priority += 1
            operation.addAlternate(operation=suboperation, priority=priority)

        item.operation = operation
        for buf in buffers_to_fill:
            buf.producing = operation
            

for bom_item in boms:
    bom = bom_item['bom']
    tryton_location = bom_item['tryton_location']
    location = bom_item['location']
    operation = bom_item['operation']
    for output in bom.outputs:
        buf_name = buffer_name(output.product, tryton_location)
        item = items[output.product.id]
        buffer = frepple.buffer(name=buf_name, item=item, location=location,
            producing=operation)
        # TODO: Need to consider UOM for quantity as well as 'efficiency'
        # module
        frepple.flow(operation=operation, buffer=buffer, type='flow_end',
            quantity=output.quantity)
    for input_ in bom.inputs:
        item = items[input_.product.id]
        buf_name = buffer_name(input_.product, tryton_location)
        buffer = frepple.buffer(name=buf_name, item=item, location=location)
        # TODO: Need to consider UOM for quantity as well as efficiency
        frepple.flow(operation=operation, buffer=buffer, type='flow_start',
            quantity=-input_.quantity)


# Create Demands
SaleLine = Model.get('sale.line')
for line in SaleLine.find([
            ('product', '!=', None),
            ]):
    item = items[line.product.id]
    location = locations[line.sale.warehouse.storage_location.id]
    customer = customers[line.sale.party.id]
    buf_name = buffer_name(line.product, line.sale.warehouse.storage_location)

    operation = frepple.operation(name=line.rec_name, location=location,
        size_multiple=1.0)
    buf = frepple.buffer(name=buf_name,
        item=item, location=location)
    frepple.flow(operation=operation, buffer=buf, quantity=-1,
        type='flow_start')
    # TODO: Take UOM into account
    frepple.demand(name=line.rec_name, item=item, customer=customer,
        operation=operation, quantity=line.quantity, due=line.delivery_date)

# Create onhand
quantities = Model.get('product.product').products_by_location(locations.keys(),
    items.keys(), config.context)
for key, quantity in quantities.iteritems():
    location_id = key[0]
    product_id = key[1]
    item = items[product_id]
    buf_name = buffer_name(products[product_id], try_locations[location_id])
    frepple.buffer(name=buf_name, location=locations[location_id],
        item=item, onhand=quantity, producing=item.operation)
    

# Create purchases
PurchaseLine = Model.get('purchase.line')
for line in PurchaseLine.find([
            ('product', '!=', None),
            ('purchase.state', '=', 'confirmed'),
            ]):
    item = items[line.product.id]
    location = locations[line.purchase.warehouse.storage_location.id]
    buf_name = buffer_name(line.product,
        line.purchase.warehouse.storage_location)
    operation_name = 'Procure for %s @ %s' % (line.product.rec_name,
        line.purchase.warehouse.storage_location.rec_name)
    buf = frepple.buffer(name=buf_name, item=item,
        location=location)
    operation = frepple.operation(name=operation_name, location=location,
        size_multiple=1.0)
    frepple.flow(operation=operation, buffer=buf, quantity=1, type='flow_end')
    date = line.purchase.purchase_date or datetime.now()
    frepple.operationplan(operation=operation, end=date, start=date,
        quantity=line.quantity, locked=False)

# TODO: Create resources: Resources represent capacity. They represent a
# machine, a worker or a group of workers, or some logical limits.
WorkCenter = Model.get('production.work_center')
for work_center in WorkCenter.find([]):
    # TODO: Cost should be converted to using UOM.
    frepple.resource(name=work_center.name, cost=work_center.cost_price)




# TODO: Create setup matrices

# TODO: Create policies

# TODO:
#  - renaming an entity in OpenERP is not handled right: id remains the 
#    same in OpenERP, but the object name in frePPLe is different.
#  - Load reorder points
#  - Load loads
#  - Load WIP
#  - Unit of measures are not used

# Create Calendars
calendar = frepple.calendar_double(name="Calendar", default=5)
calendar.setValue(datetime.now() + relativedelta(months=-1),
    datetime.now() + relativedelta(years=1), 1)

# Export static information to database for django usage
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freppledb.settings")
exportfrepple()


frepple.printsize()

print_problems()

# Parameters
# plantype == 1 -> Constrained Plan
# plantype == 2 -> Unconstrained Plan
plantype = 1
if params.get('plan') == 'unconstrained':
    plantype = 2

# constraint:
#  1 -> Lead times (don't plan in the past)
#  2 -> Material supply (don't allow inventory values to go negative)
#  4 -> Capacity (don't allow to overload resources)
#  8 -> Operation fences (don't allow to create plans in the frozen fence of operations)
constraint = 0
if params.get('lead_time'):
    constraint += 1
if params.get('material'):
    constraint += 2
if params.get('capacity'):
    constraint += 4
if params.get('release_fence'):
    constraint += 8

# Solving
solver = frepple.solver_mrp(name="MRP", constraints=constraint,
    plantype=plantype, loglevel=1, iterationthreshold=1000,
    iterationaccuracy=50)
solver.solve()

# Exporting
print_problems()
save_simulation()

# Store results to django database
from freppledb.execute.export_database_plan_postgresql import exportfrepple
exportfrepple()                                                      


frepple.printsize()
