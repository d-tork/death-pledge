function (doc) {
  if (doc.doctype === 'home') {
    emit([
      doc.added_date,
      doc.status,
      doc.url,
      doc.mls_number,
      doc.full_address,
      doc._id
    ], 1);
  }
}
