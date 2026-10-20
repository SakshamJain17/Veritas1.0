import {records} from "../../../../lib/records";
export async function GET(_request:Request,{params}:{params:Promise<{id:string}>}){const{id}=await params;return Response.json(records[id]||{error:"no_public_result",record_id:id},{status:records[id]?200:404})}
