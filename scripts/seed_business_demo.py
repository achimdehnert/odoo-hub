import xmlrpc.client
from datetime import datetime, timedelta
URL = 'http://localhost:8069'
DB = 'odoo'
USER = 'admin'
PWD = 'Admin2026!'
common = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common')
uid = common.authenticate(DB, USER, PWD, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object')
def call(model, method, args=None, kw=None):
    return m.execute_kw(DB, uid, PWD, model, method, args or [], kw or {})
def sr(model, domain, fields, limit=None):
    kw = {'fields': fields}
    if limit: kw['limit'] = limit
    return call(model, 'search_read', [domain], kw)
today = datetime.now()
print('uid=' + str(uid))
partners_data = [
    ('Automobil GmbH Muenchen', 1, 0),
    ('Maschinenbau AG Stuttgart', 1, 0),
    ('Praezisionsteile Hamburg', 1, 0),
    ('Industrie Holding Berlin', 1, 0),
    ('Giesserei Rhein-Main', 1, 0),
    ('Zulieferer Nord AG', 0, 1),
    ('Technik Sued GmbH', 1, 0),
]
pids = []
for name, crank, srank in partners_data:
    ex = call('res.partner', 'search', [[('name', '=', name)]])
    if ex:
        pids.append(ex[0])
        print('SKIP partner ' + name)
    else:
        pid = call('res.partner', 'create', [{'name': name, 'is_company': True, 'customer_rank': crank, 'supplier_rank': srank, 'country_id': 82}])
        pids.append(pid)
        print('OK partner ' + name + ' id=' + str(pid))
cids = pids[:5]
sid = pids[5]
prods = [
    ('Gussgehaeuse Typ A', 285.0, 142.0, 'consu'),
    ('Aluminiumguss B2', 420.5, 210.0, 'consu'),
    ('Stahlguss-Flansch DN100', 175.0, 87.5, 'consu'),
    ('Praezisionswelle 40mm', 320.0, 160.0, 'consu'),
    ('Montage-Dienstleistung', 95.0, 45.0, 'service'),
    ('Qualitaetspruefung', 150.0, 60.0, 'service'),
    ('Rohling Al-Si12', 55.0, 38.0, 'consu'),
    ('Schmiermittel 5L', 42.0, 22.0, 'consu'),
]
ppids = []
for name, lp, sp, ptype in prods:
    ex = call('product.template', 'search', [[('name', '=', name)]])
    if ex:
        pp = call('product.product', 'search', [[('product_tmpl_id', '=', ex[0])]])
        ppids.append(pp[0] if pp else ex[0])
        print('SKIP prod ' + name)
    else:
        tid = call('product.template', 'create', [{'name': name, 'list_price': lp, 'standard_price': sp, 'type': ptype}])
        pp = call('product.product', 'search', [[('product_tmpl_id', '=', tid)]])
        ppids.append(pp[0] if pp else tid)
        print('OK prod ' + name + ' tid=' + str(tid))
stages = sr('crm.stage', [], ['id', 'name'])
stage_ids = [s['id'] for s in stages]
print('Stages: ' + str([s['name'] for s in stages]))
leads = [
    ('Gussgehaeuse-Serie 500 St', cids[0], 142500, 80),
    ('Aluminium-Druckguss Anfrage', cids[1], 85000, 60),
    ('Flansch Rahmenvertrag', cids[2], 210000, 40),
    ('Praezisionswellen X7', cids[3], 64000, 90),
    ('Exportauftrag Q3', cids[4], 38500, 25),
    ('Wartungsvertrag 2026', cids[0], 28800, 70),
    ('Technik Sued Grossauftrag', cids[1], 320000, 35),
]
for i, (name, pid, rev, prob) in enumerate(leads):
    ex = call('crm.lead', 'search', [[('name', '=', name)]])
    if ex:
        print('SKIP lead ' + name)
        continue
    d = {'name': name, 'partner_id': pid, 'expected_revenue': rev, 'probability': prob}
    if stage_ids: d['stage_id'] = stage_ids[i % len(stage_ids)]
    lid = call('crm.lead', 'create', [d])
    print('OK lead ' + name + ' id=' + str(lid))
so_data = [
    (cids[0], 5,  [(ppids[0], 50, 285.0), (ppids[4], 10, 95.0)], True),
    (cids[1], 12, [(ppids[1], 30, 420.5), (ppids[5], 5, 150.0)], True),
    (cids[2], 20, [(ppids[2], 100, 175.0)], True),
    (cids[3], 3,  [(ppids[3], 20, 320.0)], False),
    (cids[4], 35, [(ppids[0], 25, 285.0), (ppids[2], 40, 175.0)], True),
    (cids[0], 50, [(ppids[1], 15, 420.5)], True),
    (cids[1], 60, [(ppids[3], 10, 320.0)], True),
    (cids[2], 8,  [(ppids[0], 75, 275.0)], True),
]
for cpid, days, lines, confirm in so_data:
    ol = [(0, 0, {'product_id': p, 'product_uom_qty': q, 'price_unit': pr}) for p, q, pr in lines]
    soid = call('sale.order', 'create', [{'partner_id': cpid, 'date_order': (today - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S'), 'order_line': ol}])
    if confirm: call('sale.order', 'action_confirm', [[soid]])
    print('OK SO id=' + str(soid) + ' confirm=' + str(confirm))
accs = sr('account.account', [('account_type', '=', 'income'), ('deprecated', '=', False)], ['id'], 1)
acc_id = accs[0]['id'] if accs else None
inv_data = [
    (cids[0], 30, 15675.0, True),
    (cids[1], 25, 13365.0, True),
    (cids[2], 18, 19250.0, True),
    (cids[3], 10, 8250.0,  True),
    (cids[4], 5,  11537.5, False),
    (cids[0], 50, 6307.5,  True),
    (cids[1], 65, 4550.0,  True),
]
for cpid, days, amt, post in inv_data:
    inv_date = (today - timedelta(days=days)).strftime('%Y-%m-%d')
    line = {'name': 'Lieferung', 'quantity': 1, 'price_unit': amt}
    if acc_id: line['account_id'] = acc_id
    iid = call('account.move', 'create', [{'move_type': 'out_invoice', 'partner_id': cpid, 'invoice_date': inv_date, 'invoice_line_ids': [(0, 0, line)]}])
    if post: call('account.move', 'action_post', [[iid]])
    print('OK Invoice id=' + str(iid) + ' amt=' + str(amt))
po_data = [
    (sid, 15, [(ppids[6], 200, 38.0), (ppids[7], 50, 22.0)], True),
    (sid, 28, [(ppids[6], 500, 36.0)], True),
    (sid, 5,  [(ppids[7], 100, 21.5)], False),
]
for spid, days, lines, confirm in po_data:
    pol = [(0, 0, {'product_id': p, 'product_qty': q, 'price_unit': pr, 'name': 'Zukauf', 'date_planned': (today + timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')}) for p, q, pr in lines]
    poid = call('purchase.order', 'create', [{'partner_id': spid, 'date_order': (today - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S'), 'order_line': pol}])
    if confirm: call('purchase.order', 'button_confirm', [[poid]])
    print('OK PO id=' + str(poid))
print('==> SEED DONE')
