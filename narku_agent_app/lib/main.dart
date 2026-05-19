import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart'; // NEW IMPORT

// CONFIG: Your Server URL
const String baseUrl = "[http://192.168.1.15:8000](http://192.168.1.15:8000)"; 

void main() {
  runApp(const MaterialApp(
    debugShowCheckedModeBanner: false,
    home: ChatScreen()
  ));
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, String>> _messages = [];
  bool _isLoading = false;

  Future<void> _sendMessage() async {
    if (_controller.text.isEmpty) return;
    final String userPrompt = _controller.text;

    setState(() {
      _messages.add({"role": "user", "content": userPrompt});
      _isLoading = true;
    });
    _controller.clear();

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"prompt": userPrompt}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _messages.add({"role": "agent", "content": data["response"]});
        });
      } else {
        throw Exception("Server Error: ${response.statusCode}");
      }
    } catch (e) {
      setState(() {
        _messages.add({"role": "error", "content": "Error: $e"});
      });
    } finally {
      setState(() { _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("AI Agent"),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const HistoryScreen()),
              );
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(10), // Add some padding around the list
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final msg = _messages[index];
                  final isUser = msg["role"] == "user";
                  return Align(
                    alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      constraints: BoxConstraints(
                        maxWidth: MediaQuery.of(context).size.width * 0.85, // Limit width
                      ),
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: isUser ? Colors.blue : Colors.grey[200],
                        borderRadius: BorderRadius.only(
                          topLeft: const Radius.circular(12),
                          topRight: const Radius.circular(12),
                          bottomLeft: isUser ? const Radius.circular(12) : Radius.zero,
                          bottomRight: isUser ? Radius.zero : const Radius.circular(12),
                        ),
                      ),
                      // --- NEW: MARKDOWN RENDERER ---
                      child: MarkdownBody(
                        data: msg["content"]!,
                        selectable: true, // Allows user to copy the code!
                        styleSheet: MarkdownStyleSheet(
                          p: TextStyle(color: isUser ? Colors.white : Colors.black),
                          // Style for code blocks (``` ... ```)
                          codeblockDecoration: BoxDecoration(
                            color: isUser ? Colors.blue[900] : Colors.black87,
                            borderRadius: BorderRadius.circular(5),
                          ),
                          code: const TextStyle(
                            color: Colors.white,
                            backgroundColor: Colors.transparent,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ),
                      // -----------------------------
                    ),
                  );
                },
              ),
            ),
            if (_isLoading) const LinearProgressIndicator(),
            Container(
              padding: const EdgeInsets.all(8.0),
              color: Colors.white,
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 4, // Allows input to grow if typing long requests
                      decoration: InputDecoration(
                        hintText: "Ask for code (e.g., 'Write a pong game in Python')",
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(20)),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 15, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.send, color: Colors.blue),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// (Keep your HistoryScreen class exactly as it was in the previous step)
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic> _history = [];
  bool _isLoading = true;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory([String? query]) async {
    setState(() { _isLoading = true; });
    try {
      String url = '$baseUrl/history';
      if (query != null && query.isNotEmpty) {
        url += '?q=$query';
      }

      final response = await http.get(Uri.parse(url));

      if (response.statusCode == 200) {
        setState(() {
          _history = jsonDecode(response.body);
        });
      }
    } catch (e) {
      print("Error fetching history: $e");
    } finally {
      setState(() { _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Search History")),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: "Search conversations...",
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _searchController.clear();
                    _fetchHistory();
                  },
                ),
              ),
              onChanged: (value) {
                _fetchHistory(value);
              },
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : ListView.separated(
                    itemCount: _history.length,
                    separatorBuilder: (_, __) => const Divider(),
                    itemBuilder: (context, index) {
                      final item = _history[index];
                      return ListTile(
                        title: Text(
                          item["prompt"],
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        // Also use Markdown for history preview so it looks clean
                        subtitle: SizedBox(
                          height: 50,
                          child: MarkdownBody(
                            data: item["response"], 
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}