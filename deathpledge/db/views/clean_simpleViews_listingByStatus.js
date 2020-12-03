function (doc) {
  if (doc.doctype === 'home') {
  emit(doc.address, doc.status);
  }
}
