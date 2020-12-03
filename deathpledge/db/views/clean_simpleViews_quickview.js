function (doc) {
  emit(
    doc._id, 
    [doc.status, 
    doc.added_date,
    doc.full_address,
    doc.work_commute, 
    doc.first_walk_mins, 
    doc.first_leg_type,
    doc.beds, doc.baths, 
    doc.list_price, 
    doc.condocoop_fee,
    doc.Windmill_Hill_Park_time,
    doc.tether,
    doc.nearby_metro
    ]);
}
