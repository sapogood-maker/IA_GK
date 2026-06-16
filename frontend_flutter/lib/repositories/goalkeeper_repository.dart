import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/goalkeeper.dart';

class GoalkeeperRepository {
  final String _baseUrl = 'http://your-backend-url/api/v1/goalkeepers';

  Future<Goalkeeper> createGoalkeeper(Goalkeeper goalkeeper) async {
    final response = await http.post(
      Uri.parse(_baseUrl),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(goalkeeper.toJson()),
    );

    if (response.statusCode == 201) {
      return Goalkeeper.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to create goalkeeper');
    }
  }
}
