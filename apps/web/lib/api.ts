export const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8002";
export type Doc={id:string;name:string;mime:string;size:number;sha256:string;created_at:string;claim_count?:number;status_counts?:Record<string,number>;page_count?:number};
export type Claim={id:string;document_id:string;field:string;original_value:string;normalized_value:string|null;status:string;page:number;bbox:string;confidence:number};
export type Evidence={id:string;claim_id:string;investigation_id:string|null;url:string;method:string;excerpt:string;content_sha256:string;checks:string;created_at:string};
export type Run={id:string;kind:string;status:string;request:string;result:string|null;error:string|null;started_at:string;finished_at:string|null;poll_error?:string};
export type Source={id:string;hostname:string;claim_types:string;authority:string;created_at:string};
export type AuditEvent={id:string;event:string;subject_id:string;detail:string;created_at:string};
export type Attestation={id:string;claim_id:string;status:string;issuer:string;hash:string;revoked:number;created_at:string};
export type ReviewEntry={id:string;decision:string;reason:string;corrected_value:string|null;created_at:string};
export type Decision={id:string;status:string;reason_code:string|null;checks:string;created_at:string};
export type History={reviews:ReviewEntry[];decisions:Decision[]};
export type Plan={capability:string;reason:string;approved_source:boolean;budget:{max_attempts:number;max_duration_seconds:number}};
export function human(value:string){return value.replaceAll("_"," ")}
export function parse<T>(value:string|null,fallback:T):T{try{const parsed=value?JSON.parse(value):null;return parsed===null?fallback:parsed as T}catch{return fallback}}
export async function request<T>(path:string,options?:RequestInit):Promise<T>{
 const response=await fetch(API+path,{...options,credentials:"include"});
 const data=await response.json();
 if(!response.ok){const detail=data.detail;throw new Error(typeof detail==="string"?detail:Array.isArray(detail)?detail.map((x:{msg:string})=>x.msg).join(". "):`Request failed (${response.status})`)}
 return data as T;
}
export function post<T>(path:string,body:unknown){return request<T>(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})}
export function message(error:unknown){return error instanceof Error?error.message:String(error)}
export function date(value:string){return new Date(value).toLocaleString(undefined,{month:"short",day:"numeric",year:"numeric",hour:"2-digit",minute:"2-digit"})}
export function size(value:number){return value>1048576?`${(value/1048576).toFixed(1)} MB`:`${Math.max(1,Math.round(value/1024))} KB`}
