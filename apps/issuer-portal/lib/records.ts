export type RegistryRecord={record_id:string;owner_name:string;area:string;issue_date:string;jurisdiction:string;issuer:string;status:string};
export const registryBase=process.env.NEXT_PUBLIC_REGISTRY_BASE_PATH||'';
export const records:Record<string,RegistryRecord>={
 "VR-1042":{record_id:"VR-1042",owner_name:"Ramesh Kumar",area:"2 acres",issue_date:"2024-08-14",jurisdiction:"Pune",issuer:"VERITAS Demo Registry",status:"active"},
 "VR-1043":{record_id:"VR-1043",owner_name:"Suresh Kumar",area:"2 acres",issue_date:"2024-08-16",jurisdiction:"Pune",issuer:"VERITAS Demo Registry",status:"active"},
 "VR-1044":{record_id:"VR-1044",owner_name:"Anita Deshmukh",area:"0.80937 hectares",issue_date:"2024-09-01",jurisdiction:"Nashik",issuer:"VERITAS Demo Registry",status:"active"}
};
