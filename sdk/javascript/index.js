/**
 * EthGuardian JavaScript SDK
 * AI-Powered Ethereum AML & Forensics Platform
 */

const axios = require('axios');

class EthGuardianClient {
  /**
   * Initialize EthGuardian client
   * @param {string} baseUrl - Base URL of the API
   * @param {string|null} apiKey - Optional API key
   */
  constructor(baseUrl = 'http://localhost:8000', apiKey = null) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.client = axios.create({
      baseURL: `${this.baseUrl}/api`,
      headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}
    });
  }

  // Core Analysis
  async ingest(address) {
    const { data } = await this.client.post(`/ingest/${address}`);
    return data;
  }

  async analyze(address) {
    const { data } = await this.client.post(`/analyze/${address}`);
    return data;
  }

  async getProfile(address) {
    const { data } = await this.client.get(`/profile/${address}`);
    return data;
  }

  async getGraph(address) {
    const { data } = await this.client.get(`/graph/${address}`);
    return data;
  }

  async getAlerts() {
    const { data } = await this.client.get('/alerts');
    return data;
  }

  // Pattern Detection
  async detectPatterns(address) {
    const { data } = await this.client.get(`/patterns/${address}`);
    return data;
  }

  async detectLayering(address) {
    const { data } = await this.client.get(`/patterns/${address}/layering`);
    return data;
  }

  async detectPeelChains(address) {
    const { data } = await this.client.get(`/patterns/${address}/peel-chains`);
    return data;
  }

  async detectWashTrading(address) {
    const { data } = await this.client.get(`/patterns/${address}/wash-trading`);
    return data;
  }

  // Fraud Detection
  async detectFraud(address) {
    const { data } = await this.client.get(`/fraud/${address}`);
    return data;
  }

  async detectRugPull(address) {
    const { data } = await this.client.get(`/fraud/${address}/rug-pull`);
    return data;
  }

  async detectPonzi(address) {
    const { data } = await this.client.get(`/fraud/${address}/ponzi`);
    return data;
  }

  async detectPhishing(address) {
    const { data } = await this.client.get(`/fraud/${address}/phishing`);
    return data;
  }

  async detectMevBot(address) {
    const { data } = await this.client.get(`/fraud/${address}/mev-bot`);
    return data;
  }

  // Advanced Detection
  async detectMixerUsage(address) {
    const { data } = await this.client.get(`/advanced/mixer/${address}`);
    return data;
  }

  async analyzeSmartContracts(address) {
    const { data } = await this.client.get(`/advanced/contracts/${address}`);
    return data;
  }

  async analyzeTokenHoldings(address) {
    const { data } = await this.client.get(`/advanced/tokens/${address}`);
    return data;
  }

  async detectBridgeUsage(address) {
    const { data } = await this.client.get(`/advanced/bridges/${address}`);
    return data;
  }

  async analyzeAllAdvanced(address) {
    const { data } = await this.client.get(`/advanced/all/${address}`);
    return data;
  }

  // NFT Fraud
  async detectNftWashTrading(address) {
    const { data } = await this.client.get(`/nft/wash-trading/${address}`);
    return data;
  }

  async detectFakeCollection(contract) {
    const { data } = await this.client.get(`/nft/fake-collection/${contract}`);
    return data;
  }

  async trackStolenNft(contract, tokenId) {
    const { data } = await this.client.get(`/nft/stolen/${contract}/${tokenId}`);
    return data;
  }

  // Machine Learning
  async predictFutureRisk(address, forecastDays = 7) {
    const { data } = await this.client.get(`/ml/lstm/${address}`, {
      params: { forecast_days: forecastDays }
    });
    return data;
  }

  async detectAnomaliesML(address) {
    const { data } = await this.client.get(`/ml/autoencoder/${address}`);
    return data;
  }

  async hierarchicalClustering(minAddresses = 10) {
    const { data } = await this.client.get('/ml/clustering', {
      params: { min_addresses: minAddresses }
    });
    return data;
  }

  async deepPatternRecognition(address) {
    const { data } = await this.client.get(`/ml/deep-pattern/${address}`);
    return data;
  }

  // Cross-Chain
  async detectCrossChainMovement(address, chain = 'ethereum') {
    const { data } = await this.client.get(`/cross-chain/movement/${address}`, {
      params: { chain }
    });
    return data;
  }

  async correlateAddresses(address) {
    const { data } = await this.client.get(`/cross-chain/correlation/${address}`);
    return data;
  }

  async assessMultiChainRisk(address) {
    const { data } = await this.client.get(`/cross-chain/risk/${address}`);
    return data;
  }

  // Case Management
  async createCase(title, address, caseType, priority, assignedTo, createdBy, description = null) {
    const { data } = await this.client.post('/cases/create', {
      title, address, case_type: caseType, priority,
      assigned_to: assignedTo, created_by: createdBy, description
    });
    return data;
  }

  async getCase(caseId, user, userRole) {
    const { data } = await this.client.get(`/cases/${caseId}`, {
      params: { user, user_role: userRole }
    });
    return data;
  }

  async getUserCases(user, userRole, statusFilter = null) {
    const { data } = await this.client.get(`/cases/user/${user}`, {
      params: { user_role: userRole, status_filter: statusFilter }
    });
    return data;
  }

  // Compliance
  async generateSAR(address, analyst, findings) {
    const { data } = await this.client.post('/compliance/sar', {
      address, analyst, findings
    });
    return data;
  }

  async generateCTR(address, amount, analyst) {
    const { data } = await this.client.post('/compliance/ctr', {
      address, amount, analyst
    });
    return data;
  }

  async checkCompliance(address) {
    const { data } = await this.client.get(`/compliance/check/${address}`);
    return data;
  }

  // Reports
  async generatePdfReport(address) {
    const { data } = await this.client.post('/reports/pdf', {
      address, format: 'pdf'
    });
    return data;
  }

  async generateExcelReport(address) {
    const { data } = await this.client.post('/reports/excel', { address });
    return data;
  }

  // Watchlist
  async addToWatchlist(address, reason, addedBy, riskThreshold = 70, autoAlert = true) {
    const { data } = await this.client.post('/watchlist/add', {
      address, reason, added_by: addedBy,
      risk_threshold: riskThreshold, auto_alert: autoAlert
    });
    return data;
  }

  async getWatchlist() {
    const { data } = await this.client.get('/watchlist');
    return data;
  }

  async removeFromWatchlist(address) {
    const { data } = await this.client.delete(`/watchlist/${address}`);
    return data;
  }

  async startWatchlistMonitoring() {
    const { data } = await this.client.post('/watchlist/monitoring/start');
    return data;
  }

  async stopWatchlistMonitoring() {
    const { data } = await this.client.post('/watchlist/monitoring/stop');
    return data;
  }

  // Bulk Analysis
  async bulkAnalyze(addresses, maxWorkers = 5) {
    const { data } = await this.client.post('/bulk/analyze', {
      addresses, max_workers: maxWorkers
    });
    return data;
  }

  // Graph Tools
  async shortestPath(fromAddress, toAddress) {
    const { data } = await this.client.get('/graph/shortest-path', {
      params: { from_address: fromAddress, to_address: toAddress }
    });
    return data;
  }

  async commonNeighbors(address1, address2) {
    const { data } = await this.client.get('/graph/common-neighbors', {
      params: { address1, address2 }
    });
    return data;
  }

  async detectCommunity(address) {
    const { data } = await this.client.get(`/graph/community/${address}`);
    return data;
  }

  // Webhooks
  async registerWebhook(url, events, userId, secret = null) {
    const { data } = await this.client.post('/webhooks/register', {
      url, events, user_id: userId, secret
    });
    return data;
  }

  async getUserWebhooks(userId) {
    const { data } = await this.client.get(`/webhooks/user/${userId}`);
    return data;
  }

  async deleteWebhook(webhookId, userId) {
    const { data } = await this.client.delete(`/webhooks/${webhookId}`, {
      params: { user_id: userId }
    });
    return data;
  }

  async testWebhook(webhookId) {
    const { data } = await this.client.post(`/webhooks/${webhookId}/test`);
    return data;
  }
}

module.exports = EthGuardianClient;

