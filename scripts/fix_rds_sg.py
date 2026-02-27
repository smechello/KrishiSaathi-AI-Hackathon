#!/usr/bin/env python3
"""Find RDS security group and add inbound rule for PostgreSQL from VPC CIDR."""
import boto3

ec2 = boto3.client("ec2", region_name="ap-south-1")
rds = boto3.client("rds", region_name="ap-south-1")

# Step 1: Get RDS instance's security groups
print("=== RDS Instance Security Groups ===")
try:
    resp = rds.describe_db_instances(DBInstanceIdentifier="krishisaathidb")
    db = resp["DBInstances"][0]
    rds_sgs = db.get("VpcSecurityGroups", [])
    for sg in rds_sgs:
        print(f"  {sg['VpcSecurityGroupId']} (Status: {sg['Status']})")
    rds_sg_id = rds_sgs[0]["VpcSecurityGroupId"] if rds_sgs else None
except Exception as e:
    print(f"  Error getting RDS SGs (may need AmazonRDSFullAccess): {e}")
    rds_sg_id = None

# Step 2: List all security groups in VPC
print("\n=== All Security Groups ===")
sgs = ec2.describe_security_groups()
for sg in sgs["SecurityGroups"]:
    print(f"  {sg['GroupId']}  {sg['GroupName']:30s}  VPC: {sg.get('VpcId','')}")

# Step 3: Check inbound rules on the RDS security group
if rds_sg_id:
    print(f"\n=== Inbound Rules for RDS SG: {rds_sg_id} ===")
    sg_detail = ec2.describe_security_groups(GroupIds=[rds_sg_id])
    rules = sg_detail["SecurityGroups"][0].get("IpPermissions", [])
    if not rules:
        print("  No inbound rules! This is why connection times out.")
    for rule in rules:
        proto = rule.get("IpProtocol", "")
        from_port = rule.get("FromPort", "")
        to_port = rule.get("ToPort", "")
        cidrs = [c["CidrIp"] for c in rule.get("IpRanges", [])]
        sg_refs = [s["GroupId"] for s in rule.get("UserIdGroupPairs", [])]
        print(f"  Proto: {proto}, Ports: {from_port}-{to_port}, CIDRs: {cidrs}, SGs: {sg_refs}")

    # Step 4: Add inbound rule for PostgreSQL from VPC CIDR
    has_5432_vpc = any(
        r.get("FromPort") == 5432 and 
        any(c["CidrIp"] == "172.31.0.0/16" for c in r.get("IpRanges", []))
        for r in rules
    )
    if not has_5432_vpc:
        print(f"\n  Adding PostgreSQL (5432) inbound rule from 172.31.0.0/16 ...")
        ec2.authorize_security_group_ingress(
            GroupId=rds_sg_id,
            IpPermissions=[{
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "IpRanges": [{"CidrIp": "172.31.0.0/16", "Description": "PostgreSQL from VPC"}],
            }],
        )
        print("  ✅ Inbound rule added!")
    else:
        print("  ✅ PostgreSQL rule from VPC CIDR already exists.")
