"""Demonstration of Phase 2 RF Data Processing with real S4P files."""

from pathlib import Path
from src.core.rf_data.touchstone_loader import TouchstoneLoader
from src.core.rf_data.s_parameter_calculator import SParameterCalculator

def demo_phase2():
    """Demonstrate RF data processing with real files."""
    
    print("=" * 80)
    print("RF Performance Tool - Phase 2 Demonstration")
    print("=" * 80)
    print()
    
    loader = TouchstoneLoader()
    calculator = SParameterCalculator()
    
    # Load the two S4P files
    pri_file = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_PRI.s4p")
    red_file = Path("tests/data/20250930_S-Par-SIT_Run1_L109908_SN0001_RED.s4p")
    
    print("Loading Files:")
    print("-" * 80)
    
    # Parse and load PRI file
    pri_network, pri_metadata = loader.load_with_metadata(pri_file)
    print(f"File 1: {pri_file.name}")
    print(f"  - Serial Number: {pri_metadata['serial_number']}")
    print(f"  - Part Number: {pri_metadata['part_number']}")
    print(f"  - Path Type: {pri_metadata['path_type']}")
    print(f"  - Temperature: {pri_metadata['temperature']}")
    print(f"  - Date: {pri_metadata['date']}")
    print(f"  - Network Ports: {pri_network.nports}")
    print(f"  - Frequency Points: {len(pri_network.f)}")
    print(f"  - Frequency Range: {pri_network.f[0]/1e9:.3f} - {pri_network.f[-1]/1e9:.3f} GHz")
    print()
    
    # Parse and load RED file
    red_network, red_metadata = loader.load_with_metadata(red_file)
    print(f"File 2: {red_file.name}")
    print(f"  - Serial Number: {red_metadata['serial_number']}")
    print(f"  - Part Number: {red_metadata['part_number']}")
    print(f"  - Path Type: {red_metadata['path_type']}")
    print(f"  - Temperature: {red_metadata['temperature']}")
    print(f"  - Date: {red_metadata['date']}")
    print(f"  - Network Ports: {red_network.nports}")
    print(f"  - Frequency Points: {len(red_network.f)}")
    print(f"  - Frequency Range: {red_network.f[0]/1e9:.3f} - {red_network.f[-1]/1e9:.3f} GHz")
    print()
    
    # Available S-parameters
    print("Available S-Parameters:")
    print("-" * 80)
    pri_s_params = calculator.get_available_s_params(pri_network)
    print(f"  PRI: {', '.join(pri_s_params)}")
    red_s_params = calculator.get_available_s_params(red_network)
    print(f"  RED: {', '.join(red_s_params)}")
    print()
    
    # Define operational frequency range (example: 0.5-2.0 GHz)
    op_freq_min = 0.5  # GHz
    op_freq_max = 2.0  # GHz
    
    print("=" * 80)
    print("S-Parameter Calculations")
    print("=" * 80)
    print()
    print(f"Operational Frequency Range: {op_freq_min} - {op_freq_max} GHz")
    print()
    
    # Test calculations for each S-parameter
    for s_param in ["S21", "S31", "S41"]:
        if s_param not in pri_s_params:
            continue
            
        print(f"S-Parameter: {s_param}")
        print("-" * 80)
        
        # PRI calculations
        print("  PRI Path:")
        pri_min_gain, pri_max_gain = calculator.calculate_gain_range(
            pri_network, op_freq_min, op_freq_max, s_param
        )
        pri_flatness = calculator.calculate_flatness(
            pri_network, op_freq_min, op_freq_max, s_param
        )
        pri_lowest = calculator.calculate_lowest_in_band_gain(
            pri_network, op_freq_min, op_freq_max, s_param
        )
        
        print(f"    Gain Range: {pri_min_gain:.2f} to {pri_max_gain:.2f} dB")
        print(f"    Flatness (max - min): {pri_flatness:.2f} dB")
        print(f"    Lowest In-Band Gain: {pri_lowest:.2f} dB")
        
        # RED calculations
        print("  RED Path:")
        red_min_gain, red_max_gain = calculator.calculate_gain_range(
            red_network, op_freq_min, op_freq_max, s_param
        )
        red_flatness = calculator.calculate_flatness(
            red_network, op_freq_min, op_freq_max, s_param
        )
        red_lowest = calculator.calculate_lowest_in_band_gain(
            red_network, op_freq_min, op_freq_max, s_param
        )
        
        print(f"    Gain Range: {red_min_gain:.2f} to {red_max_gain:.2f} dB")
        print(f"    Flatness (max - min): {red_flatness:.2f} dB")
        print(f"    Lowest In-Band Gain: {red_lowest:.2f} dB")
        print()
        
        # OOB rejection examples
        print(f"  OOB Rejection (relative to lowest in-band gain):")
        oob_freqs = [0.2, 3.0, 4.0]  # Example OOB frequencies
        for oob_freq in oob_freqs:
            pri_oob = calculator.calculate_oob_rejection(
                pri_network, oob_freq, op_freq_min, op_freq_max, s_param
            )
            red_oob = calculator.calculate_oob_rejection(
                red_network, oob_freq, op_freq_min, op_freq_max, s_param
            )
            print(f"    {oob_freq} GHz:")
            print(f"      PRI: {pri_oob:.2f} dBc")
            print(f"      RED: {red_oob:.2f} dBc")
        print()
    
    # VSWR calculations
    print("=" * 80)
    print("VSWR Calculations")
    print("=" * 80)
    print()
    
    for port in [1, 2]:
        pri_vswr = calculator.calculate_vswr(
            pri_network, port=port, freq_min=op_freq_min, freq_max=op_freq_max
        )
        red_vswr = calculator.calculate_vswr(
            red_network, port=port, freq_min=op_freq_min, freq_max=op_freq_max
        )
        print(f"Port {port} (Max VSWR over {op_freq_min}-{op_freq_max} GHz):")
        print(f"  PRI: {pri_vswr:.2f}")
        print(f"  RED: {red_vswr:.2f}")
        print()
    
    print("=" * 80)
    print("Example Compliance Evaluation")
    print("=" * 80)
    print()
    print("Example Criteria for S21:")
    print("  - Gain Range: 27.5 to 31.3 dB")
    print("  - Flatness: <= 2.3 dB")
    print("  - VSWR Port 1: <= 2.0")
    print()
    
    s_param = "S21"
    
    # PRI evaluation
    print("PRI Path Evaluation:")
    pri_min, pri_max = calculator.calculate_gain_range(
        pri_network, op_freq_min, op_freq_max, s_param
    )
    pri_flat = calculator.calculate_flatness(
        pri_network, op_freq_min, op_freq_max, s_param
    )
    pri_vswr = calculator.calculate_vswr(
        pri_network, port=1, freq_min=op_freq_min, freq_max=op_freq_max
    )
    
    gain_pass = 27.5 <= pri_min and pri_max <= 31.3
    flat_pass = pri_flat <= 2.3
    vswr_pass = pri_vswr <= 2.0
    
    print(f"  Gain Range: {pri_min:.2f} to {pri_max:.2f} dB")
    print(f"    Criteria: 27.5 to 31.3 dB")
    print(f"    Result: {'PASS' if gain_pass else 'FAIL'}")
    print()
    print(f"  Flatness: {pri_flat:.2f} dB")
    print(f"    Criteria: <= 2.3 dB")
    print(f"    Result: {'PASS' if flat_pass else 'FAIL'}")
    print()
    print(f"  VSWR Port 1: {pri_vswr:.2f}")
    print(f"    Criteria: <= 2.0")
    print(f"    Result: {'PASS' if vswr_pass else 'FAIL'}")
    print()
    
    # RED evaluation
    print("RED Path Evaluation:")
    red_min, red_max = calculator.calculate_gain_range(
        red_network, op_freq_min, op_freq_max, s_param
    )
    red_flat = calculator.calculate_flatness(
        red_network, op_freq_min, op_freq_max, s_param
    )
    red_vswr = calculator.calculate_vswr(
        red_network, port=1, freq_min=op_freq_min, freq_max=op_freq_max
    )
    
    gain_pass = 27.5 <= red_min and red_max <= 31.3
    flat_pass = red_flat <= 2.3
    vswr_pass = red_vswr <= 2.0
    
    print(f"  Gain Range: {red_min:.2f} to {red_max:.2f} dB")
    print(f"    Criteria: 27.5 to 31.3 dB")
    print(f"    Result: {'PASS' if gain_pass else 'FAIL'}")
    print()
    print(f"  Flatness: {red_flat:.2f} dB")
    print(f"    Criteria: <= 2.3 dB")
    print(f"    Result: {'PASS' if flat_pass else 'FAIL'}")
    print()
    print(f"  VSWR Port 1: {red_vswr:.2f}")
    print(f"    Criteria: <= 2.0")
    print(f"    Result: {'PASS' if vswr_pass else 'FAIL'}")
    print()
    
    print("=" * 80)
    print("Demonstration Complete")
    print("=" * 80)

if __name__ == "__main__":
    demo_phase2()










