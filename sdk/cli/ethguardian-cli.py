#!/usr/bin/env python3
"""
EthGuardian CLI Tool
Command-line interface for EthGuardian AML Platform
"""

import sys
import argparse
import json
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from ethguardian import EthGuardianClient


def format_json(data):
    """Pretty print JSON"""
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='EthGuardian CLI - AI-Powered Ethereum AML & Forensics'
    )
    
    parser.add_argument('--url', default='http://localhost:8000',
                       help='API base URL (default: http://localhost:8000)')
    parser.add_argument('--api-key', help='API key for authentication')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest address data')
    ingest_parser.add_argument('address', help='Ethereum address')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze address')
    analyze_parser.add_argument('address', help='Ethereum address')
    
    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Get address profile')
    profile_parser.add_argument('address', help='Ethereum address')
    
    # Graph command
    graph_parser = subparsers.add_parser('graph', help='Get transaction graph')
    graph_parser.add_argument('address', help='Ethereum address')
    
    # Alerts command
    subparsers.add_parser('alerts', help='List all alerts')
    
    # Patterns command
    patterns_parser = subparsers.add_parser('patterns', help='Detect patterns')
    patterns_parser.add_argument('address', help='Ethereum address')
    patterns_parser.add_argument('--type', choices=['layering', 'peel-chains', 'wash-trading', 'all'],
                                default='all', help='Pattern type')
    
    # Fraud command
    fraud_parser = subparsers.add_parser('fraud', help='Detect fraud')
    fraud_parser.add_argument('address', help='Ethereum address')
    fraud_parser.add_argument('--type', choices=['rug-pull', 'ponzi', 'phishing', 'mev-bot', 'all'],
                             default='all', help='Fraud type')
    
    # Mixer command
    mixer_parser = subparsers.add_parser('mixer', help='Detect mixer usage')
    mixer_parser.add_argument('address', help='Ethereum address')
    
    # NFT command
    nft_parser = subparsers.add_parser('nft', help='NFT fraud detection')
    nft_parser.add_argument('--wash-trading', metavar='ADDRESS', help='Detect wash trading')
    nft_parser.add_argument('--fake-collection', metavar='CONTRACT', help='Detect fake collection')
    nft_parser.add_argument('--stolen', nargs=2, metavar=('CONTRACT', 'TOKEN_ID'),
                           help='Track stolen NFT')
    
    # ML command
    ml_parser = subparsers.add_parser('ml', help='Machine learning analysis')
    ml_parser.add_argument('address', help='Ethereum address')
    ml_parser.add_argument('--type', choices=['lstm', 'autoencoder', 'deep-pattern', 'all'],
                          default='all', help='ML analysis type')
    
    # Cross-chain command
    cross_chain_parser = subparsers.add_parser('cross-chain', help='Cross-chain analysis')
    cross_chain_parser.add_argument('address', help='Ethereum address')
    cross_chain_parser.add_argument('--type', choices=['movement', 'correlation', 'risk', 'all'],
                                    default='all', help='Analysis type')
    
    # Watchlist command
    watchlist_parser = subparsers.add_parser('watchlist', help='Manage watchlist')
    watchlist_parser.add_argument('--add', metavar='ADDRESS', help='Add to watchlist')
    watchlist_parser.add_argument('--remove', metavar='ADDRESS', help='Remove from watchlist')
    watchlist_parser.add_argument('--list', action='store_true', help='List watchlist')
    watchlist_parser.add_argument('--reason', help='Reason for adding (required with --add)')
    watchlist_parser.add_argument('--added-by', help='Added by (required with --add)')
    watchlist_parser.add_argument('--start', action='store_true', help='Start monitoring')
    watchlist_parser.add_argument('--stop', action='store_true', help='Stop monitoring')
    
    # Bulk analyze command
    bulk_parser = subparsers.add_parser('bulk', help='Bulk analyze addresses')
    bulk_parser.add_argument('addresses', nargs='+', help='Ethereum addresses')
    bulk_parser.add_argument('--workers', type=int, default=5, help='Number of workers')
    
    # Case command
    case_parser = subparsers.add_parser('case', help='Case management')
    case_parser.add_argument('--create', action='store_true', help='Create case')
    case_parser.add_argument('--get', metavar='CASE_ID', help='Get case')
    case_parser.add_argument('--list', metavar='USER', help='List user cases')
    case_parser.add_argument('--title', help='Case title (for create)')
    case_parser.add_argument('--address', help='Address (for create)')
    case_parser.add_argument('--type', help='Case type (for create)')
    case_parser.add_argument('--priority', help='Priority (for create)')
    case_parser.add_argument('--assigned-to', help='Assigned to (for create)')
    case_parser.add_argument('--created-by', help='Created by (for create)')
    case_parser.add_argument('--user-role', default='analyst', help='User role')
    
    # Compliance command
    compliance_parser = subparsers.add_parser('compliance', help='Compliance reports')
    compliance_parser.add_argument('address', help='Ethereum address')
    compliance_parser.add_argument('--sar', action='store_true', help='Generate SAR')
    compliance_parser.add_argument('--ctr', action='store_true', help='Generate CTR')
    compliance_parser.add_argument('--check', action='store_true', help='Check compliance')
    compliance_parser.add_argument('--analyst', help='Analyst name')
    compliance_parser.add_argument('--findings', help='Findings (for SAR)')
    compliance_parser.add_argument('--amount', type=float, help='Amount (for CTR)')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('address', help='Ethereum address')
    report_parser.add_argument('--format', choices=['pdf', 'excel', 'html', 'json'],
                              default='pdf', help='Report format')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize client
    client = EthGuardianClient(base_url=args.url, api_key=args.api_key)
    
    try:
        # Execute command
        result = None
        
        if args.command == 'ingest':
            result = client.ingest(args.address)
        
        elif args.command == 'analyze':
            result = client.analyze(args.address)
        
        elif args.command == 'profile':
            result = client.get_profile(args.address)
        
        elif args.command == 'graph':
            result = client.get_graph(args.address)
        
        elif args.command == 'alerts':
            result = client.get_alerts()
        
        elif args.command == 'patterns':
            if args.type == 'all':
                result = client.detect_patterns(args.address)
            elif args.type == 'layering':
                result = client.detect_layering(args.address)
            elif args.type == 'peel-chains':
                result = client.detect_peel_chains(args.address)
            elif args.type == 'wash-trading':
                result = client.detect_wash_trading(args.address)
        
        elif args.command == 'fraud':
            if args.type == 'all':
                result = client.detect_fraud(args.address)
            elif args.type == 'rug-pull':
                result = client.detect_rug_pull(args.address)
            elif args.type == 'ponzi':
                result = client.detect_ponzi(args.address)
            elif args.type == 'phishing':
                result = client.detect_phishing(args.address)
            elif args.type == 'mev-bot':
                result = client.detect_mev_bot(args.address)
        
        elif args.command == 'mixer':
            result = client.detect_mixer_usage(args.address)
        
        elif args.command == 'nft':
            if args.wash_trading:
                result = client.detect_nft_wash_trading(args.wash_trading)
            elif args.fake_collection:
                result = client.detect_fake_collection(args.fake_collection)
            elif args.stolen:
                result = client.track_stolen_nft(args.stolen[0], args.stolen[1])
        
        elif args.command == 'ml':
            if args.type == 'all':
                result = {
                    'lstm': client.predict_future_risk(args.address),
                    'autoencoder': client.detect_anomalies_ml(args.address),
                    'deep_pattern': client.deep_pattern_recognition(args.address)
                }
            elif args.type == 'lstm':
                result = client.predict_future_risk(args.address)
            elif args.type == 'autoencoder':
                result = client.detect_anomalies_ml(args.address)
            elif args.type == 'deep-pattern':
                result = client.deep_pattern_recognition(args.address)
        
        elif args.command == 'cross-chain':
            if args.type == 'all':
                result = {
                    'movement': client.detect_cross_chain_movement(args.address),
                    'correlation': client.correlate_addresses(args.address),
                    'risk': client.assess_multi_chain_risk(args.address)
                }
            elif args.type == 'movement':
                result = client.detect_cross_chain_movement(args.address)
            elif args.type == 'correlation':
                result = client.correlate_addresses(args.address)
            elif args.type == 'risk':
                result = client.assess_multi_chain_risk(args.address)
        
        elif args.command == 'watchlist':
            if args.add:
                if not args.reason or not args.added_by:
                    print("Error: --reason and --added-by required with --add")
                    return 1
                result = client.add_to_watchlist(args.add, args.reason, args.added_by)
            elif args.remove:
                result = client.remove_from_watchlist(args.remove)
            elif args.list:
                result = client.get_watchlist()
            elif args.start:
                result = client.start_watchlist_monitoring()
            elif args.stop:
                result = client.stop_watchlist_monitoring()
        
        elif args.command == 'bulk':
            result = client.bulk_analyze(args.addresses, args.workers)
        
        elif args.command == 'case':
            if args.create:
                if not all([args.title, args.address, args.type, args.priority,
                           args.assigned_to, args.created_by]):
                    print("Error: All fields required for case creation")
                    return 1
                result = client.create_case(
                    args.title, args.address, args.type, args.priority,
                    args.assigned_to, args.created_by
                )
            elif args.get:
                result = client.get_case(args.get, 'cli_user', args.user_role)
            elif args.list:
                result = client.get_user_cases(args.list, args.user_role)
        
        elif args.command == 'compliance':
            if args.check:
                result = client.check_compliance(args.address)
            elif args.sar:
                if not args.analyst or not args.findings:
                    print("Error: --analyst and --findings required for SAR")
                    return 1
                result = client.generate_sar(args.address, args.analyst, args.findings)
            elif args.ctr:
                if not args.analyst or not args.amount:
                    print("Error: --analyst and --amount required for CTR")
                    return 1
                result = client.generate_ctr(args.address, args.amount, args.analyst)
        
        elif args.command == 'report':
            if args.format == 'pdf':
                result = client.generate_pdf_report(args.address)
            elif args.format == 'excel':
                result = client.generate_excel_report(args.address)
        
        # Print result
        if result:
            print(format_json(result))
            return 0
        else:
            print("No result returned")
            return 1
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

