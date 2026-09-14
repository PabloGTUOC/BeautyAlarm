class Product {
  final int id;
  final String name;
  final String? brand;
  final String? notes;

  Product({
    required this.id,
    required this.name,
    this.brand,
    this.notes,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'],
      name: json['name'],
      brand: json['brand'],
      notes: json['notes'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'brand': brand,
      'notes': notes,
    };
  }
}
