// mobile-app/App.js
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  FlatList,
  ActivityIndicator,
  Alert,
  Image,
  RefreshControl,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import Ionicons from 'react-native-vector-icons/Ionicons';
import AsyncStorage from '@react-native-async-storage/async-storage';

// API Configuration
const API_BASE_URL = 'http://YOUR_IP:8080'; // Change to your MCP Studio IP
const API_KEY = 'your-api-key-here'; // Get this from MCP Studio

// Main App Component
export default function App() {
  return (
    <NavigationContainer>
      <TabNavigator />
    </NavigationContainer>
  );
}

// Tab Navigator
const Tab = createBottomTabNavigator();
function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;
          if (route.name === 'Chat') iconName = focused ? 'chatbubbles' : 'chatbubbles-outline';
          else if (route.name === 'Tools') iconName = focused ? 'hammer' : 'hammer-outline';
          else if (route.name === 'Models') iconName = focused ? 'cube' : 'cube-outline';
          else if (route.name === 'Workflows') iconName = focused ? 'git-branch' : 'git-branch-outline';
          else if (route.name === 'Settings') iconName = focused ? 'settings' : 'settings-outline';
          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: 'gray',
      })}>
      <Tab.Screen name="Chat" component={ChatScreen} />
      <Tab.Screen name="Tools" component={ToolsScreen} />
      <Tab.Screen name="Models" component={ModelsScreen} />
      <Tab.Screen name="Workflows" component={WorkflowsScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}

// Chat Screen
function ChatScreen({ navigation }) {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [connectedServers, setConnectedServers] = useState([]);

  useEffect(() => {
    loadChatHistory();
    fetchConnectedServers();
  }, []);

  const loadChatHistory = async () => {
    try {
      const history = await AsyncStorage.getItem('chat_history');
      if (history) setMessages(JSON.parse(history));
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const fetchConnectedServers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/servers`, {
        headers: { 'X-API-Key': API_KEY },
      });
      const data = await response.json();
      setConnectedServers(data.servers);
    } catch (error) {
      console.error('Error fetching servers:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Save user message
      await saveMessage(userMessage);

      // Send to API
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          message: inputText,
          model: 'llama3.1',
        }),
      });

      const data = await response.json();

      const aiMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        model: data.model,
      };

      setMessages(prev => [...prev, aiMessage]);
      await saveMessage(aiMessage);
    } catch (error) {
      Alert.alert('Error', 'Failed to send message');
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveMessage = async (message) => {
    try {
      const history = await AsyncStorage.getItem('chat_history');
      const messages = history ? JSON.parse(history) : [];
      messages.push(message);
      await AsyncStorage.setItem('chat_history', JSON.stringify(messages.slice(-50))); // Keep last 50 messages
    } catch (error) {
      console.error('Error saving message:', error);
    }
  };

  const clearChat = async () => {
    Alert.alert(
      'Clear Chat',
      'Are you sure you want to clear all messages?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            setMessages([]);
            await AsyncStorage.removeItem('chat_history');
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MCP Studio Chat</Text>
        <TouchableOpacity onPress={clearChat} style={styles.clearButton}>
          <Ionicons name="trash-outline" size={24} color="#FF3B30" />
        </TouchableOpacity>
      </View>

      {/* Server Status */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.serverStatusContainer}>
        {connectedServers.map(server => (
          <View key={server.name} style={styles.serverBadge}>
            <Ionicons 
              name="checkmark-circle" 
              size={16} 
              color={server.status === 'connected' ? '#34C759' : '#FF9500'} 
            />
            <Text style={styles.serverBadgeText}>{server.name}</Text>
          </View>
        ))}
      </ScrollView>

      {/* Chat Messages */}
      <FlatList
        data={messages}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <View style={[
            styles.messageContainer,
            item.role === 'user' ? styles.userMessage : styles.aiMessage
          ]}>
            <View style={styles.messageHeader}>
              <Text style={styles.messageRole}>
                {item.role === 'user' ? 'You' : 'AI'}
              </Text>
              {item.model && (
                <Text style={styles.messageModel}>{item.model}</Text>
              )}
              <Text style={styles.messageTime}>
                {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </Text>
            </View>
            <Text style={styles.messageContent}>{item.content}</Text>
          </View>
        )}
        contentContainerStyle={styles.messagesList}
        inverted={false}
      />

      {/* Input Area */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.textInput}
          placeholder="Type your message here..."
          value={inputText}
          onChangeText={setInputText}
          multiline
          onSubmitEditing={sendMessage}
          editable={!isLoading}
        />
        <TouchableOpacity
          style={[styles.sendButton, isLoading && styles.sendButtonDisabled]}
          onPress={sendMessage}
          disabled={isLoading}>
          {isLoading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Ionicons name="send" size={24} color="#FFFFFF" />
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// Tools Screen
function ToolsScreen() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const [toolInputs, setToolInputs] = useState({});
  const [executionResult, setExecutionResult] = useState(null);

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tools`, {
        headers: { 'X-API-Key': API_KEY },
      });
      const data = await response.json();
      setTools(data.tools);
    } catch (error) {
      Alert.alert('Error', 'Failed to fetch tools');
      console.error('Tools fetch error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchTools();
  };

  const executeTool = async (tool) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/tools/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          server: tool.server,
          tool: tool.name,
          arguments: toolInputs[tool.name] || {},
        }),
      });

      const data = await response.json();
      setExecutionResult({
        tool: tool.name,
        result: data.result,
        timestamp: new Date().toISOString(),
      });

      Alert.alert('Success', 'Tool executed successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to execute tool');
      console.error('Tool execution error:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderToolItem = ({ item }) => (
    <TouchableOpacity
      style={styles.toolCard}
      onPress={() => setSelectedTool(item)}>
      <View style={styles.toolHeader}>
        <Ionicons name="hammer-outline" size={24} color="#007AFF" />
        <View style={styles.toolInfo}>
          <Text style={styles.toolName}>{item.name}</Text>
          <Text style={styles.toolServer}>{item.server}</Text>
        </View>
      </View>
      <Text style={styles.toolDescription} numberOfLines={2}>
        {item.description}
      </Text>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>MCP Tools</Text>
        <TouchableOpacity onPress={onRefresh}>
          <Ionicons name="refresh" size={24} color="#007AFF" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={tools}
        renderItem={renderToolItem}
        keyExtractor={item => `${item.server}-${item.name}`}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="hammer-outline" size={64} color="#C7C7CC" />
            <Text style={styles.emptyStateText}>No tools available</Text>
            <Text style={styles.emptyStateSubtext}>Connect to servers to see tools</Text>
          </View>
        }
        contentContainerStyle={styles.toolsList}
      />

      {/* Tool Execution Modal */}
      {selectedTool && (
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Execute: {selectedTool.name}</Text>
              <TouchableOpacity onPress={() => setSelectedTool(null)}>
                <Ionicons name="close" size={24} color="#000" />
              </TouchableOpacity>
            </View>
            
            <TextInput
              style={styles.jsonInput}
              placeholder={`Enter JSON arguments for ${selectedTool.name}`}
              multiline
              numberOfLines={6}
              value={JSON.stringify(toolInputs[selectedTool.name] || {}, null, 2)}
              onChangeText={(text) => {
                try {
                  const parsed = JSON.parse(text);
                  setToolInputs(prev => ({
                    ...prev,
                    [selectedTool.name]: parsed,
                  }));
                } catch (e) {
                  // Keep as text if invalid JSON
                }
              }}
            />

            <TouchableOpacity
              style={styles.executeButton}
              onPress={() => executeTool(selectedTool)}>
              <Text style={styles.executeButtonText}>Execute Tool</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

// Models Screen
function ModelsScreen() {
  const [models, setModels] = useState([]);
  const [marketplaceModels, setMarketplaceModels] = useState([]);
  const [activeTab, setActiveTab] = useState('local');

  useEffect(() => {
    if (activeTab === 'local') {
      fetchLocalModels();
    } else {
      fetchMarketplaceModels();
    }
  }, [activeTab]);

  const fetchLocalModels = async () => {
    try {
      // This would call your API to get local models
      const response = await fetch(`${API_BASE_URL}/api/models`, {
        headers: { 'X-API-Key': API_KEY },
      });
      const data = await response.json();
      setModels(data.models || []);
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const fetchMarketplaceModels = async () => {
    try {
      const response = await fetch('https://api.example.com/marketplace/models');
      const data = await response.json();
      setMarketplaceModels(data);
    } catch (error) {
      console.error('Error fetching marketplace models:', error);
    }
  };

  const downloadModel = async (modelId) => {
    Alert.alert(
      'Download Model',
      'This will download the model to your MCP Studio. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Download',
          onPress: async () => {
            try {
              await fetch(`${API_BASE_URL}/api/models/download`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-API-Key': API_KEY,
                },
                body: JSON.stringify({ model_id: modelId }),
              });
              Alert.alert('Success', 'Model download started');
            } catch (error) {
              Alert.alert('Error', 'Failed to download model');
            }
          },
        },
      ]
    );
  };

  const renderModelItem = ({ item }) => (
    <View style={styles.modelCard}>
      <View style={styles.modelHeader}>
        <Ionicons name="cube-outline" size={32} color="#007AFF" />
        <View style={styles.modelInfo}>
          <Text style={styles.modelName}>{item.name}</Text>
          <Text style={styles.modelDescription}>{item.description}</Text>
          <View style={styles.modelStats}>
            <Text style={styles.modelStat}>Size: {item.size}</Text>
            <Text style={styles.modelStat}>Downloads: {item.downloads}</Text>
            <Text style={styles.modelStat}>Rating: {item.rating}/5</Text>
          </View>
        </View>
      </View>
      <TouchableOpacity
        style={styles.downloadButton}
        onPress={() => downloadModel(item.id)}>
        <Text style={styles.downloadButtonText}>Download</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Models</Text>
      </View>

      {/* Tab Bar */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'local' && styles.activeTab]}
          onPress={() => setActiveTab('local')}>
          <Text style={[styles.tabText, activeTab === 'local' && styles.activeTabText]}>
            Local Models
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'marketplace' && styles.activeTab]}
          onPress={() => setActiveTab('marketplace')}>
          <Text style={[styles.tabText, activeTab === 'marketplace' && styles.activeTabText]}>
            Marketplace
          </Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={activeTab === 'local' ? models : marketplaceModels}
        renderItem={renderModelItem}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.modelsList}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="cube-outline" size={64} color="#C7C7CC" />
            <Text style={styles.emptyStateText}>No models found</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

// Workflows Screen
function WorkflowsScreen() {
  const [workflows, setWorkflows] = useState([]);
  const [showCreator, setShowCreator] = useState(false);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Workflows</Text>
        <TouchableOpacity 
          style={styles.createButton}
          onPress={() => setShowCreator(true)}>
          <Ionicons name="add" size={24} color="#FFFFFF" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.workflowsList}>
        {workflows.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="git-branch-outline" size={64} color="#C7C7CC" />
            <Text style={styles.emptyStateText}>No workflows yet</Text>
            <Text style={styles.emptyStateSubtext}>Create your first workflow to automate tasks</Text>
            <TouchableOpacity 
              style={styles.primaryButton}
              onPress={() => setShowCreator(true)}>
              <Text style={styles.primaryButtonText}>Create Workflow</Text>
            </TouchableOpacity>
          </View>
        ) : (
          workflows.map(workflow => (
            <View key={workflow.id} style={styles.workflowCard}>
              <View style={styles.workflowHeader}>
                <Ionicons name="git-branch" size={24} color="#007AFF" />
                <Text style={styles.workflowName}>{workflow.name}</Text>
              </View>
              <Text style={styles.workflowDescription}>{workflow.description}</Text>
              <View style={styles.workflowActions}>
                <TouchableOpacity style={styles.actionButton}>
                  <Text style={styles.actionButtonText}>Run</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.actionButton}>
                  <Text style={styles.actionButtonText}>Edit</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.actionButton, styles.dangerButton]}>
                  <Text style={styles.actionButtonText}>Delete</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}
      </ScrollView>

      {/* Workflow Creator Modal */}
      {showCreator && (
        <WorkflowCreator
          visible={showCreator}
          onClose={() => setShowCreator(false)}
          onSave={(workflow) => {
            setWorkflows(prev => [...prev, workflow]);
            setShowCreator(false);
          }}
        />
      )}
    </SafeAreaView>
  );
}

// Settings Screen
function SettingsScreen() {
  const [apiUrl, setApiUrl] = useState(API_BASE_URL);
  const [apiKey, setApiKey] = useState(API_KEY);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  const saveSettings = async () => {
    try {
      await AsyncStorage.setItem('settings', JSON.stringify({
        apiUrl,
        apiKey,
        notificationsEnabled,
        darkMode,
      }));
      Alert.alert('Success', 'Settings saved successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const testConnection = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/health`, {
        headers: { 'X-API-Key': apiKey },
      });
      if (response.ok) {
        Alert.alert('Success', 'Connected to MCP Studio API');
      } else {
        Alert.alert('Error', 'Failed to connect to API');
      }
    } catch (error) {
      Alert.alert('Error', 'Connection failed');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.settingsContainer}>
        <Text style={styles.sectionTitle}>API Configuration</Text>
        
        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>API URL</Text>
          <TextInput
            style={styles.settingInput}
            value={apiUrl}
            onChangeText={setApiUrl}
            placeholder="http://192.168.1.100:8080"
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>API Key</Text>
          <TextInput
            style={styles.settingInput}
            value={apiKey}
            onChangeText={setApiKey}
            placeholder="Your API key"
            secureTextEntry
          />
        </View>

        <TouchableOpacity style={styles.testButton} onPress={testConnection}>
          <Text style={styles.testButtonText}>Test Connection</Text>
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>Preferences</Text>
        
        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Enable Notifications</Text>
          <TouchableOpacity onPress={() => setNotificationsEnabled(!notificationsEnabled)}>
            <Ionicons 
              name={notificationsEnabled ? "toggle" : "toggle-outline"} 
              size={32} 
              color={notificationsEnabled ? "#34C759" : "#C7C7CC"} 
            />
          </TouchableOpacity>
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Dark Mode</Text>
          <TouchableOpacity onPress={() => setDarkMode(!darkMode)}>
            <Ionicons 
              name={darkMode ? "toggle" : "toggle-outline"} 
              size={32} 
              color={darkMode ? "#34C759" : "#C7C7CC"} 
            />
          </TouchableOpacity>
        </View>

        <Text style={styles.sectionTitle}>About</Text>
        
        <View style={styles.aboutCard}>
          <Text style={styles.appName}>MCP Studio Mobile</Text>
          <Text style={styles.appVersion}>Version 1.0.0</Text>
          <Text style={styles.appDescription}>
            Mobile client for MCP Studio - Control your AI workflows on the go
          </Text>
        </View>

        <TouchableOpacity style={styles.saveButton} onPress={saveSettings}>
          <Text style={styles.saveButtonText}>Save Settings</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

// Workflow Creator Component
function WorkflowCreator({ visible, onClose, onSave }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [steps, setSteps] = useState([]);

  const saveWorkflow = () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Please enter a workflow name');
      return;
    }

    const workflow = {
      id: Date.now().toString(),
      name,
      description,
      steps,
      created: new Date().toISOString(),
    };

    onSave(workflow);
  };

  if (!visible) return null;

  return (
    <View style={styles.creatorModal}>
      <View style={styles.creatorContent}>
        <View style={styles.creatorHeader}>
          <Text style={styles.creatorTitle}>Create Workflow</Text>
          <TouchableOpacity onPress={onClose}>
            <Ionicons name="close" size={24} color="#000" />
          </TouchableOpacity>
        </View>

        <TextInput
          style={styles.creatorInput}
          placeholder="Workflow Name"
          value={name}
          onChangeText={setName}
        />

        <TextInput
          style={[styles.creatorInput, styles.creatorTextArea]}
          placeholder="Description (optional)"
          value={description}
          onChangeText={setDescription}
          multiline
          numberOfLines={3}
        />

        <Text style={styles.stepsTitle}>Workflow Steps</Text>
        
        <ScrollView style={styles.stepsContainer}>
          {steps.map((step, index) => (
            <View key={index} style={styles.stepItem}>
              <Text style={styles.stepNumber}>Step {index + 1}</Text>
              <Text style={styles.stepName}>{step.name}</Text>
            </View>
          ))}
        </ScrollView>

        <TouchableOpacity style={styles.addStepButton}>
          <Ionicons name="add-circle-outline" size={24} color="#007AFF" />
          <Text style={styles.addStepText}>Add Step</Text>
        </TouchableOpacity>

        <View style={styles.creatorActions}>
          <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.saveWorkflowButton} onPress={saveWorkflow}>
            <Text style={styles.saveWorkflowButtonText}>Save Workflow</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000',
  },
  clearButton: {
    padding: 4,
  },
  serverStatusContainer: {
    backgroundColor: '#FFFFFF',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  serverBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  serverBadgeText: {
    fontSize: 12,
    color: '#3C3C43',
    marginLeft: 4,
  },
  messagesList: {
    padding: 16,
  },
  messageContainer: {
    marginBottom: 12,
    padding: 12,
    borderRadius: 12,
    maxWidth: '80%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#007AFF',
  },
  aiMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E5EA',
  },
  messageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  messageRole: {
    fontSize: 14,
    fontWeight: '600',
    marginRight: 8,
  },
  userMessageRole: {
    color: '#FFFFFF',
  },
  aiMessageRole: {
    color: '#000',
  },
  messageModel: {
    fontSize: 12,
    color: '#8E8E93',
    marginRight: 8,
  },
  messageTime: {
    fontSize: 11,
    color: '#8E8E93',
  },
  userMessageTime: {
    color: '#FFFFFF',
  },
  messageContent: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageContent: {
    color: '#FFFFFF',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E5E5EA',
  },
  textInput: {
    flex: 1,
    backgroundColor: '#F2F2F7',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 16,
    maxHeight: 100,
    marginRight: 12,
  },
  sendButton: {
    backgroundColor: '#007AFF',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#C7C7CC',
  },
  // Tools Screen Styles
  toolCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  toolHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  toolInfo: {
    marginLeft: 12,
    flex: 1,
  },
  toolName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
  },
  toolServer: {
    fontSize: 12,
    color: '#8E8E93',
    marginTop: 2,
  },
  toolDescription: {
    fontSize: 14,
    color: '#3C3C43',
    lineHeight: 20,
  },
  toolsList: {
    padding: 16,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyStateText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#8E8E93',
    marginTop: 16,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#C7C7CC',
    marginTop: 4,
    textAlign: 'center',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    width: '90%',
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  jsonInput: {
    borderWidth: 1,
    borderColor: '#E5E5EA',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    fontFamily: 'monospace',
    minHeight: 120,
    marginBottom: 16,
  },
  executeButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  executeButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  // Models Screen Styles
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  activeTab: {
    borderBottomColor: '#007AFF',
  },
  tabText: {
    fontSize: 16,
    color: '#8E8E93',
  },
  activeTabText: {
    color: '#007AFF',
    fontWeight: '600',
  },
  modelCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  modelHeader: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  modelInfo: {
    flex: 1,
    marginLeft: 12,
  },
  modelName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  modelDescription: {
    fontSize: 14,
    color: '#3C3C43',
    marginTop: 4,
    lineHeight: 20,
  },
  modelStats: {
    flexDirection: 'row',
    marginTop: 8,
    flexWrap: 'wrap',
  },
  modelStat: {
    fontSize: 12,
    color: '#8E8E93',
    marginRight: 16,
  },
  downloadButton: {
    backgroundColor: '#34C759',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  downloadButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  modelsList: {
    padding: 16,
  },
  // Workflows Screen Styles
  createButton: {
    backgroundColor: '#007AFF',
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  workflowsList: {
    padding: 16,
  },
  workflowCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  workflowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  workflowName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginLeft: 12,
  },
  workflowDescription: {
    fontSize: 14,
    color: '#3C3C43',
    marginBottom: 12,
    lineHeight: 20,
  },
  workflowActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  actionButton: {
    backgroundColor: '#F2F2F7',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    marginLeft: 8,
  },
  actionButtonText: {
    fontSize: 14,
    color: '#007AFF',
  },
  dangerButton: {
    backgroundColor: '#FF3B30',
  },
  dangerButtonText: {
    color: '#FFFFFF',
  },
  primaryButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginTop: 16,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  // Settings Screen Styles
  settingsContainer: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000',
    marginTop: 24,
    marginBottom: 16,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  settingLabel: {
    fontSize: 16,
    color: '#000',
  },
  settingInput: {
    flex: 1,
    fontSize: 16,
    color: '#000',
    textAlign: 'right',
    marginLeft: 16,
  },
  testButton: {
    backgroundColor: '#F2F2F7',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginBottom: 24,
  },
  testButtonText: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '600',
  },
  aboutCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  appName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginBottom: 4,
  },
  appVersion: {
    fontSize: 14,
    color: '#8E8E93',
    marginBottom: 8,
  },
  appDescription: {
    fontSize: 14,
    color: '#3C3C43',
    lineHeight: 20,
  },
  saveButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginBottom: 32,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  // Workflow Creator Styles
  creatorModal: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  creatorContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    width: '90%',
    maxHeight: '80%',
  },
  creatorHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  creatorTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000',
  },
  creatorInput: {
    backgroundColor: '#F2F2F7',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    marginBottom: 16,
  },
  creatorTextArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  stepsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    marginBottom: 12,
  },
  stepsContainer: {
    maxHeight: 200,
    marginBottom: 16,
  },
  stepItem: {
    backgroundColor: '#F2F2F7',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  stepNumber: {
    fontSize: 12,
    color: '#8E8E93',
    marginBottom: 4,
  },
  stepName: {
    fontSize: 14,
    color: '#000',
  },
  addStepButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderWidth: 2,
    borderColor: '#007AFF',
    borderStyle: 'dashed',
    borderRadius: 8,
    marginBottom: 20,
  },
  addStepText: {
    fontSize: 16,
    color: '#007AFF',
    marginLeft: 8,
  },
  creatorActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#F2F2F7',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginRight: 8,
  },
  cancelButtonText: {
    fontSize: 16,
    color: '#FF3B30',
    fontWeight: '600',
  },
  saveWorkflowButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginLeft: 8,
  },
  saveWorkflowButtonText: {
    fontSize: 16,
    color: '#FFFFFF',
    fontWeight: '600',
  },
});
