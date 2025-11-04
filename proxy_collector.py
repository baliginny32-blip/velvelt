# ipaddress.py
import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from typing import List, Dict, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IPAddressCollector:
    """
    A class to collect, validate, and manage IP addresses from various proxy sources.
    Provides legitimate IP addresses for testing and analysis purposes.
    """

    def __init__(self):
        self.proxy_sources = [
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
        ]

        self.valid_ips = []
        self.ip_details = {}
        self.validation_services = [
            "https://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "https://jsonip.com"
        ]

    def extract_ips_from_text(self, text: str) -> List[str]:
        """
        Extract IP addresses from text using regex patterns.
        Supports various formats: ip:port, http://ip:port, etc.
        """
        ip_pattern = r'\b(?:http://)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})\b'
        matches = re.findall(ip_pattern, text)

        ips = []
        for ip, port in matches:
            # Validate IP octets
            octets = ip.split('.')
            if all(0 <= int(octet) <= 255 for octet in octets):
                ips.append(f"{ip}:{port}")

        return ips

    def fetch_ips_from_source(self, source: str) -> List[str]:

        try:
            logger.info(f"📥 Fetching IPs from: {source}")
            response = requests.get(source, timeout=15)

            if response.status_code == 200:
                ips = self.extract_ips_from_text(response.text)
                logger.info(f"✅ Found {len(ips)} IPs from {source}")
                return ips
            else:
                logger.warning(f"❌ Failed to fetch from {source}: Status {response.status_code}")
                return []

        except Exception as e:
            logger.warning(f"❌ Error fetching from {source}: {str(e)}")
            return []

    def get_all_ips(self) -> List[str]:

        all_ips = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {executor.submit(self.fetch_ips_from_source, source): source
                                for source in self.proxy_sources}

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    ips = future.result()
                    all_ips.extend(ips)
                except Exception as e:
                    logger.error(f"Error processing {source}: {e}")

        # Remove duplicates while preserving order
        unique_ips = []
        seen = set()
        for ip in all_ips:
            if ip not in seen:
                seen.add(ip)
                unique_ips.append(ip)

        logger.info(f"📊 Total unique IPs collected: {len(unique_ips)}")
        return unique_ips

    def validate_ip(self, ip_address: str) -> Tuple[bool, Dict]:
        """
        Validate if an IP address is working and collect details.
        """
        proxy_url = f"http://{ip_address}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }

        validation_result = {
            'ip': ip_address,
            'working': False,
            'response_time': None,
            'detected_ip': None,
            'service_used': None,
            'error': None
        }

        for service in self.validation_services:
            try:
                start_time = time.time()
                response = requests.get(
                    service,
                    proxies=proxies,
                    timeout=10
                )
                response_time = round((time.time() - start_time) * 1000, 2)

                if response.status_code == 200:
                    # Parse response based on service
                    if service == "https://api.ipify.org?format=json":
                        ip_data = response.json()
                        detected_ip = ip_data.get('ip')
                    elif service == "https://jsonip.com":
                        ip_data = response.json()
                        detected_ip = ip_data.get('ip')
                    else:  # httpbin.org
                        ip_data = response.json()
                        detected_ip = ip_data.get('origin')

                    validation_result.update({
                        'working': True,
                        'response_time': response_time,
                        'detected_ip': detected_ip,
                        'service_used': service
                    })

                    logger.info(f"🎯 Valid IP: {ip_address} → Response: {response_time}ms")
                    return True, validation_result

            except requests.exceptions.ConnectTimeout:
                validation_result['error'] = 'Connection timeout'
                continue
            except requests.exceptions.ProxyError:
                validation_result['error'] = 'Proxy error'
                continue
            except Exception as e:
                validation_result['error'] = str(e)
                continue

        logger.debug(f"❌ Invalid IP: {ip_address} - {validation_result['error']}")
        return False, validation_result

    def get_validated_ips(self, max_ips: int = 50) -> List[Dict]:
        """
        Get validated working IP addresses with their details.
        """
        logger.info("🔄 Starting IP collection and validation...")

        # Get all IPs from sources
        all_ips = self.get_all_ips()

        if not all_ips:
            logger.warning("🚨 No IPs found from sources")
            return []

        # Validate IPs concurrently
        validated_ips = []
        working_ips = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {executor.submit(self.validate_ip, ip): ip
                            for ip in all_ips[:max_ips]}

            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    is_valid, details = future.result()
                    if is_valid:
                        working_ips.append(ip)
                        validated_ips.append(details)
                except Exception as e:
                    logger.error(f"Error validating {ip}: {e}")

        logger.info(f"✅ Validation complete: {len(working_ips)}/{len(all_ips[:max_ips])} IPs working")

        # Sort by response time (fastest first)
        validated_ips.sort(key=lambda x: x['response_time'] or float('inf'))

        return validated_ips

    def showcase_ips(self, count: int = 20):
        """
        Display a formatted showcase of legitimate IP addresses.
        """
        print("\n" + "=" * 60)
        print("🛜 LEGITIMATE IP ADDRESS SHOWCASE")
        print("=" * 60)

        validated_ips = self.get_validated_ips(max_ips=count)

        if not validated_ips:
            print("❌ No working IP addresses found!")
            return

        print(f"\n📊 Found {len(validated_ips)} working IP addresses:")
        print("-" * 80)
        print(f"{'No.':<4} {'IP Address':<20} {'Response Time':<15} {'Detected IP':<20} {'Service':<20}")
        print("-" * 80)

        for i, ip_info in enumerate(validated_ips, 1):
            ip_addr = ip_info['ip']
            response_time = f"{ip_info['response_time']}ms" if ip_info['response_time'] else "N/A"
            detected_ip = ip_info['detected_ip'] or "N/A"
            service = ip_info['service_used'] or "N/A"

            # Shorten service URL for display
            if 'httpbin' in service:
                service = 'httpbin.org'
            elif 'ipify' in service:
                service = 'ipify.org'
            elif 'jsonip' in service:
                service = 'jsonip.com'

            print(f"{i:<4} {ip_addr:<20} {response_time:<15} {detected_ip:<20} {service:<20}")

        print("-" * 80)

        # Show statistics
        avg_response_time = sum(ip['response_time'] for ip in validated_ips if ip['response_time']) / len(validated_ips)
        fastest_ip = min(validated_ips, key=lambda x: x['response_time'] or float('inf'))
        slowest_ip = max(validated_ips, key=lambda x: x['response_time'] or 0)

        print(f"\n📈 Statistics:")
        print(f"   • Average Response Time: {avg_response_time:.2f}ms")
        print(f"   • Fastest IP: {fastest_ip['ip']} ({fastest_ip['response_time']}ms)")
        print(f"   • Slowest IP: {slowest_ip['ip']} ({slowest_ip['response_time']}ms)")
        print(f"   • Total Working IPs: {len(validated_ips)}")

    def save_ips_to_file(self, filename: str = "legitimate_ips.json"):
        """
        Save validated IP addresses to a JSON file.
        """
        validated_ips = self.get_validated_ips()

        if validated_ips:
            with open(filename, 'w') as f:
                json.dump(validated_ips, f, indent=2)
            logger.info(f"💾 Saved {len(validated_ips)} IPs to {filename}")
        else:
            logger.warning("No IPs to save!")

    def get_ip_stats(self) -> Dict:
        """
        Get statistics about the collected IP addresses.
        """
        validated_ips = self.get_validated_ips()

        if not validated_ips:
            return {"error": "No validated IPs found"}

        response_times = [ip['response_time'] for ip in validated_ips if ip['response_time']]

        stats = {
            "total_working_ips": len(validated_ips),
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "fastest_response_time": min(response_times) if response_times else 0,
            "slowest_response_time": max(response_times) if response_times else 0,
            "sources_used": len(self.proxy_sources)
        }

        return stats


# Utility functions
def quick_ip_test():
    """Quick test function to demonstrate the IP collector."""
    collector = IPAddressCollector()
    collector.showcase_ips(10)


def get_fastest_ips(count: int = 5) -> List[str]:
    """Get the fastest working IP addresses."""
    collector = IPAddressCollector()
    validated_ips = collector.get_validated_ips(max_ips=count * 3)  # Get more to filter
    fastest_ips = sorted(validated_ips, key=lambda x: x['response_time'] or float('inf'))[:count]
    return [ip['ip'] for ip in fastest_ips]


# Main execution
if __name__ == "__main__":
    print("🚀 IP Address Collector - Starting...")

    collector = IPAddressCollector()

    # Showcase IPs
    collector.showcase_ips(15)

    # Save to file
    collector.save_ips_to_file()

    # Show statistics
    stats = collector.get_ip_stats()
    print(f"\n📋 Final Statistics:")
    for key, value in stats.items():
        print(f"   • {key.replace('_', ' ').title()}: {value}")