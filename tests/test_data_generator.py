from core.data_generator import CampusDataGenerator

def test_generation_schema_and_ranges():
    gen=CampusDataGenerator(days=1); zones,metrics,devices,flows=gen.generate_all()
    assert len(zones)==12 and len(metrics)==12*96
    assert {"timestamp","zone_id","download_mbps","usability_score"}<=set(metrics)
    assert metrics.usability_score.between(0,100).all()
    assert metrics.packet_loss_pct.ge(0).all()
    assert (metrics.active_devices<=metrics.merge(zones,on="zone_id").device_capacity*1.08+1).all()
    assert not devices.empty and not flows.empty

def test_fixed_seed_reproducible():
    a=CampusDataGenerator(seed=7,days=1).generate_metrics().head()
    b=CampusDataGenerator(seed=7,days=1).generate_metrics().head()
    assert a.equals(b)

