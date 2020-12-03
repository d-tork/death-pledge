function (doc) {
  if (doc.sold) {
  emit(doc.sold, {listPrice: doc.list_price, salePrice: doc.sale_price});
  }
}
